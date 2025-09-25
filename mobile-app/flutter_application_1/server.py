from flask import Flask, jsonify
import re

app = Flask(__name__)

def parse_explanation():
    appliances = {}
    with open("output_explanation.txt", "r") as f:
        content = f.read()

    # Split by appliance section
    blocks = re.split(r"--- (.*?) ---", content)
    # blocks[0] is header, then blocks[1] is first appliance name, blocks[2] is content, etc.
    for i in range(1, len(blocks), 2):
        name = blocks[i].strip()
        data = blocks[i+1]

        # Extract costs and savings
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
    return jsonify(parse_explanation())

@app.route("/schedules")
def get_schedules():
    with open("output.txt", "r") as f:
        data = f.read()
    return jsonify({"schedules": data})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
