import math
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'model'))
from predict import make_scaling_decision, calculate_replica_count, estimate_scaling_cost
from datetime import datetime


class TestEventDetection:

    def test_black_friday_detected(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 11, 27), region="US"
        )
        assert decision["should_prescale"] is True
        assert "black_friday" in decision["reason"]

    def test_great_indian_festival_detected(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 10, 7), region="IN"
        )
        assert decision["should_prescale"] is True

    def test_normal_day_no_scale(self):
        decision = make_scaling_decision(check_date=datetime(2024, 6, 15))
        assert decision["should_prescale"] is False
        assert decision["target_replicas"] == 2

    def test_replica_count_within_bounds(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 11, 27), region="US"
        )
        assert 2 <= decision["target_replicas"] <= 20

    def test_prime_day_highest_replica_count(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 7, 16), region="GLOBAL"
        )
        assert decision["target_replicas"] > 10


class TestReplicaCalculation:

    def test_event_day_full_scale(self):
        replicas = calculate_replica_count(traffic_multiplier=5.0, days_until=0)
        assert replicas == min(20, math.ceil(2 * 5.0 * 1.2))

    def test_three_days_out_less_than_day_of(self):
        replicas_day_of = calculate_replica_count(5.0, days_until=0)
        replicas_3_days = calculate_replica_count(5.0, days_until=3)
        assert replicas_3_days < replicas_day_of

    def test_never_below_baseline(self):
        replicas = calculate_replica_count(1.0, days_until=3)
        assert replicas >= 2

    def test_never_above_max(self):
        replicas = calculate_replica_count(100.0, days_until=0)
        assert replicas <= 20


class TestCostAnalysis:

    def test_cost_analysis_present_on_prescale(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 11, 27), region="US"
        )
        assert decision["cost_analysis"] is not None

    def test_cost_analysis_null_on_normal_day(self):
        decision = make_scaling_decision(check_date=datetime(2024, 6, 15))
        assert decision["cost_analysis"] is None

    def test_cost_justified_for_black_friday(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 11, 27), region="US"
        )
        assert decision["cost_analysis"]["cost_justified"] is True

    def test_extra_cost_is_positive(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 11, 27), region="US"
        )
        assert decision["cost_analysis"]["extra_scaling_cost_usd"] > 0

    def test_total_cost_greater_than_baseline(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 11, 27), region="US"
        )
        ca = decision["cost_analysis"]
        assert ca["total_cost_during_event_usd"] > ca["baseline_cost_usd"]

    def test_extra_pods_matches_replica_difference(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 11, 27), region="US"
        )
        ca = decision["cost_analysis"]
        assert ca["extra_pods"] == decision["target_replicas"] - 2

    def test_revenue_at_risk_present(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 11, 27), region="US"
        )
        assert "revenue_at_risk_if_down" in decision["cost_analysis"]
        assert len(decision["cost_analysis"]["revenue_at_risk_if_down"]) > 0

    def test_summary_string_present(self):
        decision = make_scaling_decision(
            check_date=datetime(2024, 11, 27), region="US"
        )
        assert "summary" in decision["cost_analysis"]
        assert len(decision["cost_analysis"]["summary"]) > 0
