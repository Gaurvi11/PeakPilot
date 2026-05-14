#!/bin/bash
set -e

TARGET_REPLICAS=$1
EVENT_NAME=$2
DEPLOYMENT_NAME="peakpilot-app"
NAMESPACE="peakpilot"

echo "================================================"
echo "PeakPilot Pre-Scale Triggered"
echo "Event:           $EVENT_NAME"
echo "Target replicas: $TARGET_REPLICAS"
echo "Time:            $(date)"
echo "================================================"

CURRENT=$(kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE \
    -o jsonpath='{.spec.replicas}')
echo "Current replicas: $CURRENT"

if [ "$TARGET_REPLICAS" -le "$CURRENT" ]; then
    echo "Already at or above target. No pre-scaling needed."
    exit 0
fi

echo "Scaling from $CURRENT to $TARGET_REPLICAS replicas..."
kubectl scale deployment/$DEPLOYMENT_NAME \
    -n $NAMESPACE --replicas=$TARGET_REPLICAS

echo "Waiting for pods to be ready (timeout: 3 min)..."
kubectl rollout status deployment/$DEPLOYMENT_NAME \
    -n $NAMESPACE --timeout=180s

ACTUAL=$(kubectl get deployment $DEPLOYMENT_NAME -n $NAMESPACE \
    -o jsonpath='{.spec.replicas}')
echo "Scale complete. Running replicas: $ACTUAL"

kubectl annotate deployment/$DEPLOYMENT_NAME -n $NAMESPACE \
    peakpilot/last-scale-event="$EVENT_NAME" \
    peakpilot/last-scale-time="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    peakpilot/last-scale-replicas="$TARGET_REPLICAS" \
    --overwrite

echo "================================================"
echo "Pre-scale complete."
echo "================================================"
