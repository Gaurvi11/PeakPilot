"""
PeakPilot AI Decision Engine
Phase 1: Rule-based event calendar lookup
Phase 2: Prophet-based traffic forecasting

Includes cost estimation — the engine does not just decide whether
to scale, it also calculates what that scaling costs and explicitly
states whether the cost is justified vs the risk of not scaling.
"""

import pandas as pd
import json
import os
import math
from datetime import datetime, timedelta
from dateutil import parser as dateparser

EVENTS_CSV = os.path.join(os.path.dirname(__file__), "events.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "traffic_model.json")

BASELINE_REPLICAS = 2
MAX_REPLICAS = 20
LOOKAHEAD_DAYS = 3

# Cost per pod per hour in USD (t3.medium equivalent on EKS)
# Includes: EC2 compute + EKS node overhead + rough network cost
# Adjust this constant to match your actual instance type
COST_PER_POD_PER_HOUR_USD = 0.05


def load_events():
    df = pd.read_csv(EVENTS_CSV)
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    return df


def check_upcoming_events(check_date=None):
    if check_date is None:
        check_date = datetime.now()

    check_date = pd.Timestamp(check_date)
    lookahead_end = check_date + timedelta(days=LOOKAHEAD_DAYS)

    events = load_events()
    upcoming = []

    for _, row in events.iterrows():
        if (row["start_date"] >= check_date and row["start_date"] <= lookahead_end) or \
           (row["start_date"] <= check_date <= row["end_date"]):

            days_until = max(0, (row["start_date"] - check_date).days)
            currently_active = row["start_date"] <= check_date <= row["end_date"]

            upcoming.append({
                "event_name": row["event_name"],
                "region": row["region"],
                "start_date": str(row["start_date"].date()),
                "end_date": str(row["end_date"].date()),
                "days_until": days_until,
                "currently_active": currently_active,
                "avg_traffic_multiplier": row["avg_traffic_multiplier"],
                "description": row["description"]
            })

    return sorted(upcoming, key=lambda x: x["days_until"])


def calculate_replica_count(traffic_multiplier, days_until):
    """
    Ramp up gradually based on proximity to event.
    0 days = full scale, 3 days = 50% scale.
    Always add 20% safety buffer on top.
    """
    ramp_factors = {0: 1.0, 1: 0.9, 2: 0.75, 3: 0.5}
    ramp = ramp_factors.get(days_until, 0.5)

    effective_multiplier = 1 + (traffic_multiplier - 1) * ramp
    raw_replicas = BASELINE_REPLICAS * effective_multiplier * 1.2

    return min(MAX_REPLICAS, max(BASELINE_REPLICAS, math.ceil(raw_replicas)))


def estimate_scaling_cost(target_replicas, event_details):
    """
    Calculate the cost of scaling up for this event and compare it
    against the revenue at risk if the site goes down during the event.

    This makes the cost-benefit decision explicit rather than scaling
    blindly. In production, plug in your actual revenue/minute figure.

    Key insight: extra scaling cost for most events is under $50 total.
    One minute of downtime during any of these events costs far more.
    """
    extra_pods = target_replicas - BASELINE_REPLICAS

    if extra_pods <= 0 or not event_details:
        return None

    # Calculate event duration in hours
    start = datetime.strptime(event_details["start_date"], "%Y-%m-%d")
    end = datetime.strptime(event_details["end_date"], "%Y-%m-%d")
    # Add 24 hours because end date is inclusive (1-day event = 24 hours)
    duration_hours = max(1, int((end - start).total_seconds() / 3600) + 24)

    # Cost of the extra pods during the event window
    extra_cost_usd = round(
        extra_pods * COST_PER_POD_PER_HOUR_USD * duration_hours, 2
    )

    # Cost of baseline pods for comparison
    baseline_cost_usd = round(
        BASELINE_REPLICAS * COST_PER_POD_PER_HOUR_USD * duration_hours, 2
    )

    total_cost_usd = round(extra_cost_usd + baseline_cost_usd, 2)

    # Revenue at risk context
    # These are illustrative figures based on public earnings data.
    # In production: replace with your actual revenue/minute from analytics.
    revenue_context = {
        "black_friday":          "$3-5M revenue/hour at risk",
        "prime_day":             "$5-8M revenue/hour at risk",
        "great_indian_festival": "$1-2M revenue/hour at risk",
        "singles_day":           "$8-12M revenue/hour at risk",
        "cyber_monday":          "$2-4M revenue/hour at risk",
        "diwali_sale":           "$0.5-1M revenue/hour at risk",
    }

    revenue_at_risk = revenue_context.get(
        event_details["event_name"],
        "Significant revenue at risk during peak event"
    )

    # Cost is justified when extra scaling cost is negligible
    # vs revenue at risk. $500 threshold is extremely conservative —
    # in practice extra cost is almost always under $100.
    cost_justified = extra_cost_usd < 500

    return {
        "extra_pods": extra_pods,
        "cost_per_pod_per_hour_usd": COST_PER_POD_PER_HOUR_USD,
        "event_duration_hours": duration_hours,
        "baseline_cost_usd": baseline_cost_usd,
        "extra_scaling_cost_usd": extra_cost_usd,
        "total_cost_during_event_usd": total_cost_usd,
        "revenue_at_risk_if_down": revenue_at_risk,
        "cost_justified": cost_justified,
        "summary": (
            f"Scaling costs an extra ${extra_cost_usd} over {duration_hours}h. "
            f"1 minute of downtime during {event_details['event_name']} "
            f"costs far more. Cost is justified."
            if cost_justified else
            f"Extra scaling cost ${extra_cost_usd} over {duration_hours}h. "
            f"Review whether full pre-scale is necessary."
        )
    }


def make_scaling_decision(check_date=None, region=None):
    """
    Main function: given a date and optional region,
    decide how many replicas to run.

    Returns:
      should_prescale   bool
      target_replicas   int
      reason            str
      event_details     dict or None
      confidence        HIGH / MEDIUM / LOW
      cost_analysis     dict or None
      checked_at        str
    """
    if check_date is None:
        check_date = datetime.now()

    upcoming = check_upcoming_events(check_date)

    if region and upcoming:
        upcoming = [e for e in upcoming if e["region"] in (region, "GLOBAL")]

    if not upcoming:
        return {
            "should_prescale": False,
            "target_replicas": BASELINE_REPLICAS,
            "reason": "No peak events detected within lookahead window",
            "event_details": None,
            "confidence": "HIGH",
            "cost_analysis": None,
            "checked_at": str(check_date)
        }

    top_event = max(upcoming, key=lambda x: x["avg_traffic_multiplier"])
    target_replicas = calculate_replica_count(
        top_event["avg_traffic_multiplier"],
        top_event["days_until"]
    )

    confidence = "HIGH" if top_event["days_until"] <= 1 else "MEDIUM"

    # Calculate cost analysis for this scaling decision
    cost_analysis = estimate_scaling_cost(target_replicas, top_event)

    return {
        "should_prescale": True,
        "target_replicas": target_replicas,
        "reason": (
            f"Upcoming event: {top_event['event_name']} "
            f"({top_event['days_until']} days away, "
            f"{top_event['avg_traffic_multiplier']}x expected traffic)"
        ),
        "event_details": top_event,
        "confidence": confidence,
        "cost_analysis": cost_analysis,
        "checked_at": str(check_date)
    }


if __name__ == "__main__":
    import sys
    check_date_str = sys.argv[1] if len(sys.argv) > 1 else None
    region = sys.argv[2] if len(sys.argv) > 2 else None

    check_date = dateparser.parse(check_date_str) if check_date_str else datetime.now()
    decision = make_scaling_decision(check_date=check_date, region=region)

    print(json.dumps(decision, indent=2))
    sys.exit(0 if decision["should_prescale"] else 1)
