.PHONY: setup start stop rebuild deploy ai-check test load-test logs grafana prometheus clean help

setup:
	minikube start --memory=4096 --cpus=2
	minikube addons enable metrics-server
	minikube addons enable ingress
	eval $$(minikube docker-env) && docker build -t peakpilot-app:latest ./app
	helm repo add kedacore https://kedacore.github.io/charts
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	helm repo update
	helm install keda kedacore/keda --namespace keda --create-namespace
	kubectl create namespace peakpilot || true
	kubectl apply -f k8s/

start:
	minikube start --memory=4096 --cpus=2
	eval $$(minikube docker-env)

stop:
	minikube stop

rebuild:
	eval $$(minikube docker-env) && docker build -t peakpilot-app:latest ./app
	kubectl rollout restart deployment/peakpilot-app -n peakpilot

ai-check:
	source venv/bin/activate && python3 scripts/check-event.py

test:
	source venv/bin/activate && pytest ai-engine/tests/ -v

load-test:
	k6 run \
		--env BASE_URL=$$(minikube service peakpilot-service -n peakpilot --url) \
		load-test/load_test.js

logs:
	kubectl logs -l app=peakpilot -n peakpilot --tail=100 -f

grafana:
	kubectl port-forward -n monitoring service/monitoring-grafana 3000:80 &
	open http://localhost:3000

prometheus:
	kubectl port-forward -n monitoring \
		service/monitoring-kube-prometheus-prometheus 9090:9090 &
	open http://localhost:9090

clean:
	kubectl delete -f k8s/ --ignore-not-found
	helm uninstall keda -n keda || true
	helm uninstall monitoring -n monitoring || true
	minikube stop

help:
	@echo "Available commands:"
	@echo "  make rebuild      - Rebuild Docker image and restart pods"
	@echo "  make ai-check     - Test AI decision engine"
	@echo "  make test         - Run all unit tests"
	@echo "  make load-test    - Run k6 load test"
	@echo "  make grafana      - Open Grafana dashboard"
	@echo "  make logs         - Tail pod logs"
	@echo "  make clean        - Tear everything down"
