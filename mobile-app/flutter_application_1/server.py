# server.py
from flask import Flask, jsonify, make_response
from flask_cors import CORS
import re
import time
import logging
import os

app = Flask(__name__)
CORS(app)  # <- allow all origins for development. For production, lock this down.

logging.basicConfig(level=logging.INFO)

def parse_explanation(path="output_explanation.txt"):
    appliances = {}
    if not os.path.exists(path):
        app.logger.error(f"{path} not found")
        return appliances

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Use a regex that captures sections cleanly. Expect blocks like: --- NAME ---\n...content...
    # This will return tuples of (name, content)
    pattern = re.compile(r"---\s*(.+?)\s*---\s*(.*?)(?=(?:---\s*.+?\s*---)|\Z)", re.S)
    for match in pattern.finditer(content):
        name = match.group(1).strip()
        data = match.group(2)

        # Extract costs and savings (numbers may have decimals)
        original_cost_match = re.search(r"Original cost:\s*([\d.]+)", data)
        optimized_cost_match = re.search(r"Optimized cost:\s*([\d.]+)", data)
        savings_match = re.search(r"Savings:\s*([\d.]+)", data)

        appliances[name] = {
            "original_cost": float(original_cost_match.group(1)) if original_cost_match else 0.0,
            "optimized_cost": float(optimized_cost_match.group(1)) if optimized_cost_match else 0.0,
            "savings": float(savings_match.group(1)) if savings_match else 0.0
        }

    return appliances

@app.route("/analysis")
def get_analysis():
    try:
        data = parse_explanation()
        return jsonify(data)
    except Exception as e:
        app.logger.exception("Error in /analysis")
        return make_response(jsonify({"error": "internal server error"}), 500)

@app.route("/schedules")
def get_schedules():
    try:
        if not os.path.exists("output.txt"):
            return make_response(jsonify({"error": "output.txt not found", "schedules": ""}), 404)
        with open("output.txt", "r", encoding="utf-8") as f:
            data = f.read()
        # Return schedules as a string (you already parse it on the client)
        return jsonify({"schedules": data})
    except Exception as e:
        app.logger.exception("Error in /schedules")
        return make_response(jsonify({"error": "internal server error", "schedules": ""}), 500)

@app.route("/refresh")
def refresh():
    try:
        # Here you can re-run your model or pull new data files
        # For now, we'll just note the time it was refreshed
        print(f"Data refreshed at {time.ctime()}")
        return jsonify({"status": "success", "message": "Files reloaded"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # debug True is OK for local development
    app.run(host="0.0.0.0", port=5000, debug=True)
