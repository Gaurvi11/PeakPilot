from flask import Flask, jsonify
import time, os, random

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "service": "peakpilot-ecommerce",
        "status": "healthy",
        "pod": os.environ.get("HOSTNAME", "local")
    })

@app.route("/products")
def products():
    time.sleep(random.uniform(0.01, 0.05))
    return jsonify({"products": ["item1", "item2", "item3"], "count": 3})

@app.route("/checkout")
def checkout():
    time.sleep(random.uniform(0.05, 0.1))
    return jsonify({"status": "order_placed", "order_id": random.randint(1000, 9999)})

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/metrics-demo")
def metrics():
    return jsonify({
        "requests_per_second": random.randint(50, 500),
        "active_users": random.randint(100, 10000)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
