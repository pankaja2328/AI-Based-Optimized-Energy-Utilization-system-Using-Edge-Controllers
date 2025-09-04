import paho.mqtt.client as mqtt
import time
import ast
import json
from langchain_ollama import ChatOllama
import ollama
from datetime import datetime, timedelta
import re
from typing import Dict, List, Tuple

# CONFIG
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC = "power/tou_domestic"


APPLIANCES = [
    'WashingMachine_Power',
    'Heater_Power',
    'AC_Power',
    'VehicleCharger_Power',
    'VacuumCleaner_Power'
]

POWER_KWH: Dict[str, float] = {
    'WashingMachine_Power': 0.6,   
    'Heater_Power':         2.0,
    'AC_Power':             1.2,
    'VehicleCharger_Power': 2.2,
    'VacuumCleaner_Power':  1.1,
}

USE_LLM_FOR_SCHED = True
LLM_MODEL = "llama3.2:latest" 
LLM_TEMP = 0.0


# MQTT / INPUT
def get_mqtt_power_data(timeout: int = 5):
    """
    Fetch one MQTT message (TOU rates) as string payload from the broker.
    Expected JSON payload (example):
    {
      "day":      {"time": "05:30 - 18:30", "rate": 35.0},
      "peak":     {"time": "18:30 - 22:30", "rate": 67.0},
      "off_peak": {"time": "22:30 - 05:30", "rate": 21.0}
    }
    """
    result: Dict[str, str] = {}
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.v5)
        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                client.subscribe(MQTT_TOPIC)
            else:
                result['error'] = f"Failed to connect, reason code: {reason_code}"
    except AttributeError:
        client = mqtt.Client()
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                client.subscribe(MQTT_TOPIC)
            else:
                result['error'] = f"Failed to connect, return code: {rc}"

    def on_message(client, userdata, msg):
        result['payload'] = msg.payload.decode(errors="ignore")
        client.disconnect()

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    for _ in range(timeout):
        if 'payload' in result or 'error' in result:
            break
        time.sleep(1)
    client.loop_stop()
    return result.get('payload', result.get('error', 'No data received'))


def read_appliance_status(filename: str) -> Dict[str, Dict[str, List[int]]]:
    """
    Parse appliance status file to extract original ON/OFF sequences for each appliance.
    Expected format in 'appliance_data.txt':
      --- WashingMachine_Power ---
      States:
      0,0,0,1,1,0, ... (24 ints)
    """
    status: Dict[str, Dict[str, List[int]]] = {}
    current_appliance = None
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("---") and line.endswith("---"):
            current_appliance = line.replace("-", "").strip()
            status[current_appliance] = {"states": []}
            i += 1
        elif line.lower() == "states:" and current_appliance:
            i += 1
            status[current_appliance]["states"] = [int(x.strip()) for x in lines[i].split(",") if x.strip()]
            i += 1
        else:
            i += 1
    return status


# UTILS
def parse_price_num(val) -> float:
    """Extract numeric price from strings like 'LKR 54.00' or just numbers."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        m = re.search(r"[-+]?\d*\.?\d+", val)
        if m:
            return float(m.group(0))
    return 0.0


def fix_length(arr: List[int]) -> List[int]:
    """Ensure ON/OFF array has exactly 24 values (pads/truncates) as 0/1 ints."""
    arr = [int(x) & 1 for x in list(arr)]
    if len(arr) < 24:
        arr = arr + [0] * (24 - len(arr))
    if len(arr) > 24:
        arr = arr[:24]
    return arr


def time_range_to_hours(start_time: str, end_time: str) -> List[int]:
    """
    Map a time band [start, end) to whole-hour indices [0..23].
    Minutes are ignored for the hour end (half-open interval):
      e.g., 05:30–18:30 -> [5,6,...,17]
    Supports overnight wrap (e.g., 22:30–05:30) and '24:00'.
    """
    def parse_hhmm(s: str) -> int:
        h, m = map(int, s.strip().split(":"))
        if h == 24 and m == 0:
            return 24 * 60
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError(f"Invalid HH:MM: {s}")
        return h * 60 + m

    s = parse_hhmm(start_time)
    e = parse_hhmm(end_time)
    if e <= s:
        e += 24 * 60  

    h_start = s // 60
    h_end   = e // 60 
    hours = [(h % 24) for h in range(h_start, h_end)]
    return sorted(set(hours))


def extract_first_array(text: str):
    """Extract the first [...] block from LLM output (no markdown, just the array)."""
    text = re.sub(r"```[\w\W]*?```", "", text)  # strip fenced blocks
    m = re.search(r"\[[^\[\]]{1,2000}\]", text, re.S)
    return m.group(0) if m else None


# PRICE MAP (per hour)
def build_price_map(tou_json: Dict) -> Tuple[Dict[int, Dict], str]:
    """
    Build a 24-hour price map: {hour: {"price": float, "band": "day/peak/off_peak"}}
    Accepts payloads using keys like `rate` or `price` (or `tariff`).
    Returns (price_map, currency).
    """
    # Normalize hours for each band
    for period, values in tou_json.items():
        if period in ("day", "peak", "off_peak"):
            start, end = values["time"].split(" - ")
            tou_json[period]["hours"] = time_range_to_hours(start.strip(), end.strip())

    currency = tou_json.get("currency", "LKR")

    def get_rate_value(band: dict) -> float:
        return parse_price_num(band.get("rate", band.get("price", band.get("tariff", 0))))

    day_price = get_rate_value(tou_json["day"])
    peak_price = get_rate_value(tou_json["peak"])
    off_peak_price = get_rate_value(tou_json["off_peak"])

    price_map: Dict[int, Dict] = {h: {"price": off_peak_price, "band": "off_peak"} for h in range(24)}

    for h in tou_json["day"]["hours"]:
        price_map[h] = {"price": day_price, "band": "day"}
    for h in tou_json["peak"]["hours"]:
        price_map[h] = {"price": peak_price, "band": "peak"}
    for h in tou_json["off_peak"]["hours"]:
        price_map[h] = {"price": off_peak_price, "band": "off_peak"}

    return price_map, currency


# COSTS + EXPLANATIONS
def cost_for_states(states: List[int], power_kwh: float, price_map: Dict[int, Dict]) -> float:
    return sum(int(states[h]) * power_kwh * price_map[h]["price"] for h in range(24))


def compare_and_pair_moves(orig: List[int], opt: List[int]) -> List[Tuple[int, int]]:
    """
    Greedily pair hours turned OFF in opt (were 1 in orig, now 0) with hours turned ON in opt (were 0 in orig, now 1).
    Returns list of (from_hour, to_hour) pairs representing 'moved' ONs.
    """
    removed = [h for h in range(24) if orig[h] == 1 and opt[h] == 0]
    added   = [h for h in range(24) if orig[h] == 0 and opt[h] == 1]
    pairs = []
    for i in range(min(len(removed), len(added))):
        pairs.append((removed[i], added[i]))
    return pairs


def explain_changes(appliance: str,
                    orig: List[int],
                    opt: List[int],
                    price_map: Dict[int, Dict],
                    power_kwh: float) -> Tuple[List[str], float]:
    """
    Create human-readable reasons and compute per-appliance savings.
    """
    reasons: List[str] = []
    pairs = compare_and_pair_moves(orig, opt)
    saved_total = 0.0

    if not pairs and orig == opt:
        reasons.append("No changes were required; schedule already avoided peak hours.")
    else:
        for fr, to in pairs:
            pf, bf = price_map[fr]["price"], price_map[fr]["band"]
            pt, bt = price_map[to]["price"], price_map[to]["band"]
            delta = (pf - pt) * power_kwh
            saved_total += max(0.0, delta)
            if bf == "peak" and bt != "peak":
                reasons.append(f"Shifted hour {fr:02d}:00 ({bf}, {pf}) → {to:02d}:00 ({bt}, {pt}) to avoid peak pricing.")
            elif pf > pt:
                reasons.append(f"Moved {fr:02d}:00 → {to:02d}:00 to a cheaper band ({bf}->{bt}).")
            else:
                reasons.append(f"Adjusted {fr:02d}:00 → {to:02d}:00 to respect constraints; no direct price advantage.")

    peak_on_after = [h for h in range(24) if opt[h] == 1 and price_map[h]["band"] == "peak"]
    if peak_on_after:
        hours_str = ", ".join(f"{h:02d}:00" for h in peak_on_after)
        reasons.append(f"Peak hours retained at [{hours_str}] per user permission for this appliance.")

    reasons.append(f"Original ON hours: {[h for h in range(24) if orig[h]==1]}")
    reasons.append(f"Optimized ON hours: {[h for h in range(24) if opt[h]==1]}")
    if saved_total > 0:
        reasons.append(f"Estimated savings for {appliance}: {saved_total:.2f} (currency units).")

    return reasons, saved_total

# SCHEDULING RULES / POST
def redistribute_peak_violations(schedules: Dict[str, List[int]], tou_json, allow_peak: Dict[str, bool]):
    """
    Remove ONs placed in peak hours unless allowed by user; redistribute to cheaper hours.
    """
    peak_hours = tou_json["peak"]["hours"]
    off_peak_hours = tou_json["off_peak"]["hours"]
    day_hours = tou_json["day"]["hours"]

    for appliance, arr in schedules.items():
        if allow_peak.get(appliance, False):
            continue

        removed_on_count = 0
        for h in peak_hours:
            if arr[h] == 1:
                removed_on_count += 1
                arr[h] = 0

        total_on = sum(arr) + removed_on_count
        filled = sum(arr)
        for hour_list in [off_peak_hours, day_hours, range(24)]:
            for h in hour_list:
                if h in peak_hours:
                    continue
                if arr[h] == 0 and filled < total_on:
                    arr[h] = 1
                    filled += 1
            if filled >= total_on:
                break
        schedules[appliance] = arr
    return schedules


def enforce_required_ons_improved(schedules: Dict[str, List[int]],
                                  tou_json,
                                  required_ons: Dict[str, int],
                                  allow_peak: Dict[str, bool]) -> Dict[str, List[int]]:
    """
    Ensure each appliance has exactly the same number of ONs as original (no more, no less),
    preferring to add/remove in off-peak, then day, then anywhere; never add in peak unless allowed.
    """
    peak = set(tou_json["peak"]["hours"])
    offp = [h for h in tou_json["off_peak"]["hours"]]
    day  = [h for h in tou_json["day"]["hours"] if h not in peak and h not in offp]

    for appliance, arr in schedules.items():
        need = required_ons.get(appliance, sum(arr))
        curr = sum(arr)

        def add_ones(hours):
            nonlocal arr, curr
            for h in hours:
                if curr >= need:
                    break
                if arr[h] == 0 and (allow_peak.get(appliance, False) or h not in peak):
                    arr[h] = 1
                    curr += 1

        def remove_ones(hours):
            nonlocal arr, curr
            for h in hours:
                if curr <= need:
                    break
                if arr[h] == 1:
                    arr[h] = 0
                    curr -= 1

        if curr < need:
            add_ones(offp)
            add_ones(day)
            add_ones([h for h in range(24) if allow_peak.get(appliance, False) or h not in peak])
        elif curr > need:
            remove_ones(day)
            remove_ones(offp)
            if allow_peak.get(appliance, False):
                remove_ones([h for h in range(24)])

        schedules[appliance] = fix_length(arr)
    return schedules


# LLM PROMPTS
def build_system_prompt(APPLIANCES, status, tou_json, weather, i, allow_peak):
    appliance = APPLIANCES[i]
    original = status[appliance]["states"]
    allow_peak_str = (
        f"For {appliance}, you ARE allowed to schedule ONs during peak hours if needed.\n"
        if allow_peak.get(appliance, False)
        else f"For {appliance}, you are NOT allowed to schedule ONs during peak hours.\n"
    )
    prompt = (
        "You are an Energy Scheduling Expert for a smart home.\n"
        "Here is the predicted 24-hour ON/OFF array (0 = OFF, 1 = ON) for one appliance:\n"
        f"{appliance}_Power = {original}\n\n"
        "Time bands (hours):\n"
        f"  Day: {tou_json['day']['hours']}\n"
        f"  Peak: {tou_json['peak']['hours']}\n"
        f"  Off-peak: {tou_json['off_peak']['hours']}\n\n"
        "Rules:\n"
        "  • Keep exactly the same number of 1 s as in the original list.\n"
        "  • Move every 1 that is in a peak-hour to an off-peak hour if possible.\n"
        "  • Absolutely no 1 s may remain in peak hours unless user allows it.\n"
        "  • Use only 0 s and 1 s. List length must be 24.\n\n"
        f"{allow_peak_str}"
        "Return only a Python list of 24 zeros or ones (no markdown, no commentary)."
    )
    return prompt


# OUTPUT WRITERS
def write_schedules(schedules: Dict[str, List[int]]):
    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write("Optimised Appliance Schedules (24-hour ON/OFF)\n\n")
        for name in APPLIANCES:
            arr = schedules.get(name, [])
            if len(arr) != 24:
                raise ValueError(f"{name} does not have exactly 24 states.")
            f.write(f"--- {name} ---\n")
            f.write(f"States: {arr}\n\n")
    print("Optimised ON/OFF schedules saved to output.txt")


def write_explanations(explanations: Dict, currency: str):
    """Writes a human-readable reasons + cost summary file."""
    with open('output_explanations.txt', 'w', encoding='utf-8') as f:
        f.write("Scheduling Rationale and Cost Analysis\n")
        f.write("======================================\n\n")
        for name, info in explanations["per_appliance"].items():
            f.write(f"--- {name} ---\n")
            f.write(f"Original cost: {info['original_cost']:.2f} {currency}\n")
            f.write(f"Optimized cost: {info['optimized_cost']:.2f} {currency}\n")
            f.write(f"Savings: {info['savings']:.2f} {currency}\n")
            f.write("Reasons:\n")
            for r in info["reasons"]:
                f.write(f"  - {r}\n")
            f.write("\n")

        f.write("=== TOTALS ===\n")
        f.write(f"Baseline total cost: {explanations['totals']['baseline']:.2f} {currency}\n")
        f.write(f"Optimized total cost: {explanations['totals']['optimized']:.2f} {currency}\n")
        f.write(f"Total savings: {explanations['totals']['savings']:.2f} {currency}\n")
        if explanations['totals']['baseline'] > 0:
            pct = 100.0 * explanations['totals']['savings'] / explanations['totals']['baseline']
            f.write(f"Percent savings: {pct:.2f}%\n")
    print("Explanations and cost report saved to output_explanations.txt")

# =========================
# MAIN LOOP
# =========================
def parse_user_preferences(user_msg: str) -> Dict[str, bool]:
    """
    Returns a dict: {appliance_name: allow_peak (True/False)}
    Example user_msg: "Allow AC_Power ON during peak hours"
    """
    allow_peak: Dict[str, bool] = {}
    for appliance in APPLIANCES:
        pattern = rf"Allow {appliance} ON during peak hours"
        allow_peak[appliance] = bool(re.search(pattern, user_msg, re.IGNORECASE))
    return allow_peak


def main_once():
    # 1) Read original states
    status = read_appliance_status("appliance_data.txt")

    # 2) TOU from MQTT
    tou_json_raw = get_mqtt_power_data()
    try:
        tou_json = json.loads(tou_json_raw)
    except Exception as e:
        print("Failed to parse TOU JSON from MQTT:", e)
        print("Raw payload:", tou_json_raw)
        return

    price_map, currency = build_price_map(tou_json)

    # 3) Weather (stub) – available for future LLM prompts
    weather = {
        "temperature": [25, 24, 23, 22, 22, 23, 24, 25, 26, 27, 28, 29, 30, 30, 29, 28, 27, 26, 25, 24, 23, 22, 22, 23],
        "humidity":    [60, 62, 65, 67, 70, 72, 75, 77, 80, 82, 85, 87, 90, 92, 85, 78, 70, 65, 60, 58, 56, 55, 54, 53]
    }

    # 4) User preferences (example)
    user_msg = "Allow AC_Power ON during peak hours"
    allow_peak = parse_user_preferences(user_msg)

    # 5) Build schedules
    if USE_LLM_FOR_SCHED:
        llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMP)

    schedules: Dict[str, List[int]] = {}
    required_ons: Dict[str, int] = {}

    for i, appliance in enumerate(APPLIANCES):
        original = fix_length(status.get(appliance, {}).get("states", [0]*24))
        required_ons[appliance] = sum(original)

        if USE_LLM_FOR_SCHED:
            sys_prompt = build_system_prompt(APPLIANCES, status, tou_json, weather, i, allow_peak)
            user_prompt = "Output ONLY the Python array for this appliance. No explanations, no markdown."
            max_retries = 5
            out = None
            for attempt in range(max_retries):
                try:
                    response = llm.invoke([
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt}
                    ])
                    out = response.content
                    break
                except ollama._types.ResponseError as e:
                    print(f"Ollama error: {e}. Retrying in 10s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(10)
                except Exception as e:
                    print(f"Unexpected error: {e}. Retrying in 10s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(10)

            if not out:
                print(f"LLM failed for {appliance}; falling back to original states.")
                schedules[appliance] = original
            else:
                try:
                    arr_txt = extract_first_array(out)
                    if arr_txt is None:
                        raise ValueError("No list found in LLM output.")
                    arr = fix_length(ast.literal_eval(arr_txt))
                    schedules[appliance] = arr
                except Exception as e:
                    print(f"LLM output parse error for {appliance}: {e}. Using original states.")
                    schedules[appliance] = original
        else:
            # Non-LLM fallback: just use original, then post-process
            schedules[appliance] = original

    # 6) Post-process schedules
    schedules = redistribute_peak_violations(schedules, tou_json, allow_peak)
    schedules = enforce_required_ons_improved(schedules, tou_json, required_ons, allow_peak)

    # 7) Validate values
    for a in APPLIANCES:
        arr = schedules[a]
        assert len(arr) == 24, f"{a} does not have 24 elements"
        assert all(v in [0, 1] for v in arr), f"{a} contains non-binary values"
        if not allow_peak.get(a, False):
            for h in tou_json["peak"]["hours"]:
                if arr[h] == 1:
                    raise AssertionError(f"{a} ON during forbidden peak hour {h}")

    # 8) WRITE schedules file
    write_schedules(schedules)

    # 9) COST & REASONS FILE
    explanations = {
        "per_appliance": {},
        "totals": {"baseline": 0.0, "optimized": 0.0, "savings": 0.0}
    }

    for a in APPLIANCES:
        original = fix_length(status.get(a, {}).get("states", [0]*24))
        optimized = schedules[a]
        power_kwh = POWER_KWH.get(a, 1.0)

        base_cost = cost_for_states(original, power_kwh, price_map)
        opt_cost  = cost_for_states(optimized, power_kwh, price_map)
        reasons, _ = explain_changes(a, original, optimized, price_map, power_kwh)

        explanations["per_appliance"][a] = {
            "original_cost": base_cost,
            "optimized_cost": opt_cost,
            "savings": max(0.0, base_cost - opt_cost),
            "reasons": reasons
        }
        explanations["totals"]["baseline"]  += base_cost
        explanations["totals"]["optimized"] += opt_cost

    explanations["totals"]["savings"] = max(0.0, explanations["totals"]["baseline"] - explanations["totals"]["optimized"])
    write_explanations(explanations, currency)


def main_loop():
    while True:
        main_once()
        print("Waiting 30 minutes for next run...")
        time.sleep(1800)


if __name__ == "__main__":
    main_loop()
