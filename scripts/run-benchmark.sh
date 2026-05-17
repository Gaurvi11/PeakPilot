#!/bin/bash
# Run the full benchmark: baseline vs pre-scaled
# Records results to load-test/results/

set -e
NAMESPACE="peakpilot"
RESULTS_DIR="load-test/results"
mkdir -p $RESULTS_DIR
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "================================================"
echo "PeakPilot Benchmark"
echo "Timestamp: $TIMESTAMP"
echo "================================================"

# Get service URL
SERVICE_URL=$(minikube service peakpilot-service -n $NAMESPACE --url 2>/dev/null | head -1)
echo "Service URL: $SERVICE_URL"

# Reset to baseline
echo "Resetting to 2 pods..."
kubectl scale deployment/peakpilot-app -n $NAMESPACE --replicas=2
sleep 20

# Run 1: Baseline
echo "RUN 1: Baseline (no pre-scale)..."
k6 run --env BASE_URL=$SERVICE_URL \
    --out json=$RESULTS_DIR/baseline_$TIMESTAMP.json \
    load-test/load_test.js 2>&1 | tee $RESULTS_DIR/baseline_summary_$TIMESTAMP.txt

# Reset
kubectl scale deployment/peakpilot-app -n $NAMESPACE --replicas=2
sleep 20

# Pre-scale
echo "Pre-scaling..."
./scripts/pre-scale.sh 10 "benchmark_test"
sleep 30

# Run 2: Pre-scaled
echo "RUN 2: Pre-scaled..."
k6 run --env BASE_URL=$SERVICE_URL \
    --out json=$RESULTS_DIR/prescaled_$TIMESTAMP.json \
    load-test/load_test.js 2>&1 | tee $RESULTS_DIR/prescaled_summary_$TIMESTAMP.txt

echo "Benchmark complete. Results saved to $RESULTS_DIR/"
echo "================================================"
