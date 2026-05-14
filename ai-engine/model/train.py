"""
Phase 2: Train a Prophet time-series model on historical traffic data.
Generates synthetic training data based on events.csv multipliers.
In production, replace synthetic data with real Prometheus metrics.
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

try:
    from prophet import Prophet
    from prophet.serialize import model_to_json
    USING_NEURAL = False
    PROPHET_AVAILABLE = True
except ImportError:
    try:
        from neuralprophet import NeuralProphet as Prophet
        PROPHET_AVAILABLE = True
        USING_NEURAL = True
    except ImportError:
        PROPHET_AVAILABLE = False
        print("WARNING: No Prophet library found. Skipping Phase 2 training.")

MODEL_OUTPUT = os.path.join(os.path.dirname(__file__), "traffic_model.json")
EVENTS_CSV = os.path.join(os.path.dirname(__file__), "events.csv")


def generate_synthetic_traffic(days=730):
    events = pd.read_csv(EVENTS_CSV)
    events["start_date"] = pd.to_datetime(events["start_date"])
    events["end_date"] = pd.to_datetime(events["end_date"])

    start = datetime(2023, 1, 1)
    date_range = pd.date_range(start=start, periods=days * 24, freq="h")

    traffic = []
    for dt in date_range:
        base = 1000
        hour_factor = 0.3 + 0.7 * np.sin((dt.hour - 4) * np.pi / 12) ** 2
        week_factor = 1.3 if dt.weekday() >= 5 else 1.0

        event_factor = 1.0
        for _, event in events.iterrows():
            if event["start_date"] <= dt <= event["end_date"]:
                event_factor = max(event_factor, event["avg_traffic_multiplier"])

        noise = np.random.normal(1.0, 0.05)
        traffic.append(base * hour_factor * week_factor * event_factor * noise)

    return pd.DataFrame({"ds": date_range, "y": traffic})


def train_model():
    if not PROPHET_AVAILABLE:
        return

    print("Generating 2 years of synthetic traffic data...")
    df = generate_synthetic_traffic(days=730)
    print(f"Training on {len(df)} data points...")

    events_df = pd.read_csv(EVENTS_CSV)
    holidays = pd.DataFrame({
        "holiday": events_df["event_name"],
        "ds": pd.to_datetime(events_df["start_date"]),
        "lower_window": -2,
        "upper_window": 1,
    })

    model = Prophet(
        holidays=holidays,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True,
        changepoint_prior_scale=0.05,
        holidays_prior_scale=10.0,
        seasonality_prior_scale=10.0,
    )
    model.fit(df)

    try:
        with open(MODEL_OUTPUT, "w") as f:
            json.dump(model_to_json(model), f)
        print(f"Model saved to {MODEL_OUTPUT}")
    except Exception:
        print("Model trained. Serialization skipped.")

    future = model.make_future_dataframe(periods=24 * 30, freq="h")
    forecast = model.predict(future)
    upcoming = forecast[forecast["ds"] >= datetime.now()].nlargest(5, "yhat")

    print("\nTop 5 predicted peak periods:")
    for _, row in upcoming.iterrows():
        print(f"  {row['ds'].strftime('%Y-%m-%d %H:00')} "
              f"— {row['yhat']:.0f} req/hr predicted")

    print("\nTraining complete.")


if __name__ == "__main__":
    train_model()
