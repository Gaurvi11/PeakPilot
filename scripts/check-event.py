#!/usr/bin/env python3
"""
Called by GitHub Actions during deployment.
Runs the AI engine and writes outputs the workflow reads.
Now includes cost analysis in the log output so every CI run
shows the cost justification in the Actions log.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-engine', 'model'))

from predict import make_scaling_decision


def main():
    region = os.environ.get("DEPLOY_REGION", None)
    decision = make_scaling_decision(region=region)

    print(f"Decision:\n{json.dumps(decision, indent=2)}")

    # Print cost summary separately for cleaner CI logs
    if decision.get("cost_analysis"):
        ca = decision["cost_analysis"]
        print("\n--- Cost Analysis ---")
        print(f"Extra pods:          {ca['extra_pods']}")
        print(f"Extra cost:          ${ca['extra_scaling_cost_usd']} "
              f"over {ca['event_duration_hours']}h")
        print(f"Revenue at risk:     {ca['revenue_at_risk_if_down']}")
        print(f"Cost justified:      {ca['cost_justified']}")
        print(f"Summary:             {ca['summary']}")
        print("--------------------\n")

    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"should_prescale="
                    f"{'true' if decision['should_prescale'] else 'false'}\n")
            f.write(f"target_replicas={decision['target_replicas']}\n")
            f.write(f"event_name="
                    f"{decision.get('event_details', {}).get('event_name', 'none')}\n")
            f.write(f"confidence={decision['confidence']}\n")

    print(f"should_prescale={decision['should_prescale']}")
    print(f"target_replicas={decision['target_replicas']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
