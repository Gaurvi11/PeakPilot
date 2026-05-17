# PeakPilot

> AI-driven CI/CD autoscaling system that predicts e-commerce peak traffic events
> and scales Kubernetes infrastructure proactively — before users arrive.

## The Problem

During major sale events (Black Friday, Amazon's Great Indian Festival, Prime Day),
servers crash not because engineers are slow — but because reactive autoscalers
always lag. By the time CPU spikes and pods scale up, users are already hitting errors.
Cold-start latency compounds the problem at exactly the worst moment.

## The Solution

PeakPilot embeds an AI decision engine directly into the CI/CD pipeline. Before every
deployment, it asks: "Is a peak traffic event within 72 hours?" If yes, it pre-scales
the Kubernetes cluster and warms the load balancer BEFORE the code deploys and BEFORE
users arrive.

It also calculates the cost of scaling vs the revenue at risk — making an explicit
business decision rather than scaling blindly.

## Architecture

Code push → GitHub Actions → AI Decision Engine
↓
reads: Event Calendar + Traffic Model
↓
outputs: should_prescale, target_replicas,
cost_analysis, confidence
↓
Peak event?  YES → Pre-scale pods → Deploy
NO  → Standard deploy
↓
Kubernetes + KEDA + Load Balancer
↓
Prometheus + Grafana (observability)

## Results (k6 Load Test — 500 virtual users, 5 minutes)

| Metric | Without PeakPilot | With PeakPilot | Improvement |
|--------|-------------------|----------------|-------------|
| p95 response time | 1130ms | 456ms | 2.5x faster |
| Average response time | 497ms | 110ms | 4.5x faster |
| Throughput | 252 req/s | 656 req/s | 2.6x higher |
| Error rate | 0.30% | 1.12% | — |
| Pod scale-up lag | 4-6 minutes | 0 (pre-scaled) | — |
*Tested on local Minikube cluster (MacBook M2, 16GB RAM, 2 CPUs allocated to Minikube)*
*Error rate increase in pre-scaled run reflects 2.6x higher request volume 
handled. Both runs maintained sub-2% error thresholds.*

## AI Engine — Cost Analysis Output

```json
{
  "should_prescale": true,
  "target_replicas": 10,
  "reason": "Upcoming event: black_friday (2 days away, 5.1x expected traffic)",
  "confidence": "MEDIUM",
  "cost_analysis": {
    "extra_scaling_cost_usd": 38.4,
    "event_duration_hours": 96,
    "revenue_at_risk_if_down": "$3-5M revenue/hour at risk",
    "cost_justified": true,
    "summary": "Scaling costs an extra $38.4 over 96h. 1 minute of downtime costs far more."
  }
}
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | Kubernetes (Minikube local / GKE production) |
| Event-driven autoscaling | KEDA |
| CI/CD | GitHub Actions |
| Traffic forecasting | Facebook Prophet |
| Monitoring | Prometheus + Grafana |
| Load testing | k6 |
| Containerization | Docker |
| Infrastructure as Code | Terraform (in progress) |
| Language | Python 3.11 |

## Running Locally

```bash
# Prerequisites: Docker Desktop, Minikube, Helm, Python 3.10+, k6

# Clone and setup
git clone https://github.com/YOUR_USERNAME/peakpilot
cd peakpilot
python3 -m venv venv && source venv/bin/activate
pip install -r ai-engine/requirements.txt

# Start Kubernetes
minikube start --memory=4096 --cpus=2
minikube addons enable metrics-server ingress
eval $(minikube docker-env)

# Build and deploy
docker build -t peakpilot-app:latest ./app
kubectl create namespace peakpilot
kubectl apply -f k8s/
helm install keda kedacore/keda --namespace keda --create-namespace

# Test the AI engine
python3 ai-engine/model/predict.py "2024-11-27" "US"

# Run load test
minikube service peakpilot-service -n peakpilot
k6 run --env BASE_URL=<url-from-above> load-test/load_test.js
```

## Key Design Decisions

**Why KEDA over HPA?** HPA only scales on CPU/memory. KEDA scales on any metric
including custom business signals from the AI engine.

**Why Prophet over LSTM?** Prophet decomposes time series into interpretable components
(trend, seasonality, holidays). Every scaling decision can be explained. Neural networks
cannot offer this.

**Why embed in CI/CD instead of running alongside it?** Existing solutions run as
separate infrastructure services. Embedding in the pipeline means the scaling decision
is made at the moment of deployment — the exact right time — with zero additional
infrastructure to maintain.

**Cost optimization built in:** The AI engine calculates the cost of scaling vs revenue
at risk before making a decision. It doesn't scale blindly — it justifies the spend.

## Author

Gaurvi Arora — MS Computer Science, Northeastern University (May 2027)
Targeting SRE / DevOps / Cloud Engineer roles.