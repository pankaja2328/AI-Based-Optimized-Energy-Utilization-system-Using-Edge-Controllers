#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM-First Appliance Scheduler (Edge-friendly)
- ALWAYS calls the LLM to produce a 24x binary schedule per appliance.
- Strict prompt: same # of ones as input (or MIN_ONS override).
- Deterministic fallback if LLM output is invalid.
- Robust status-file parser, MQTT v2, wrap-around time bands.
"""

import os
import re
import ast
import json
import time
from datetime import datetime

# ---------- Optional deps for LLM ----------
try:
    from langchain_ollama import ChatOllama
    import ollama  # noqa: F401
    HAS_OLLAMA = True
except Exception:
    HAS_OLLAMA = False

import paho.mqtt.client as mqtt

# ---------- Config / Env ----------
APPLIANCES = [
    "WashingMachine_Power",
    "Heater_Power",
    "AC_Power",
    "VehicleCharger_Power",
    "VacuumCleaner_Power",
]

STATUS_FILE = os.getenv("STATUS_FILE", "appliance_data.txt")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "output.txt")

MQTT_BROKER = os.getenv("MQTT_BROKER", "1b68f21e37a44697a7872f3c9321ce24.s1.eu.hivemq.cloud")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USER   = os.getenv("MQTT_USER", "malshan")
MQTT_PASS   = os.getenv("MQTT_PASS", "Pankaja1")
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "power/tou_domestic")

# LLM config (LLM is always used; fallback only if invalid)
LLM_MODEL       = os.getenv("LLM_MODEL", "llama3.2:latest")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))   # keep tight to avoid hanging
LLM_RETRY_SECS  = int(os.getenv("LLM_RETRY_SECS", "5"))

# Runtime
RUN_INTERVAL_SECS = int(os.getenv("RUN_INTERVAL_SECS", "1800"))
RUN_ONCE          = os.getenv("RUN_ONCE", "false").lower() in ("1", "true", "yes")

# Optional: enforce minimum ONs (useful if predictor outputs zeros)
# Example: MIN_ONS='{"VehicleCharger_Power":2,"WashingMachine_Power":2}'
MIN_ONS = {}
try:
    if os.getenv("MIN_ONS"):
        MIN_ONS = json.loads(os.getenv("MIN_ONS"))
except Exception:
    MIN_ONS = {}

# Optional demo generator
GENERATE_DEMO_FILE = os.getenv("GENERATE_DEMO_FILE", "false").lower() in ("1", "true", "yes")

# ---------- Helpers ----------
def _write_demo_status_file(path="appliance_data.txt"):
    demo = """\
--- WashingMachine_Power ---
States:
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0

--- Heater_Power ---
States:
[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0]

--- AC_Power ---
States:
0,
0,
0,
0,
0,
0,
0,
0,
0,
0,
0,
0,
0,
0,
0,
0,
0,
0,
1,
1,
1,
1,
0,
0

--- VehicleCharger_Power ---
States:
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1

--- VacuumCleaner_Power ---
States:
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(demo)
    print(f"✅ Wrote demo status file to {os.path.abspath(path)}")


def _parse_24_ints_from_text(txt: str):
    """Extract exactly 24 binary ints from free-form text (commas/spaces/newlines/brackets allowed)."""
    txt = txt.replace("[", " ").replace("]", " ")
    tokens = re.split(r"[,\s]+", txt.strip())
    vals = []
    for t in tokens:
        if t == "":
            continue
        if t not in ("0", "1"):
            continue
        vals.append(int(t))
        if len(vals) == 24:
            break
    return vals if len(vals) == 24 else None


def read_appliance_status(filename: str):
    """Robust parser for appliance_data.txt; accepts multiple formats per appliance."""
    path = os.path.abspath(filename)
    print(f"[STATUS] loading: {path}")
    if not os.path.exists(filename):
        print("[STATUS] file NOT found → defaulting to zeros for all appliances.")
        return {a: {"states": [0]*24} for a in APPLIANCES}

    with open(filename, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split blocks on headers like --- NAME ---
    blocks = re.split(r"\n\s*---\s*(.*?)\s*---\s*\n", "\n" + raw)
    status = {}

    if len(blocks) >= 3:
        for i in range(1, len(blocks), 2):
            name = blocks[i].strip()
            content = blocks[i+1]
            # Prefer content after "States:"
            m = re.search(r"States\s*:\s*(.*?)(?:\n\s*\n|$|^\s*---)", content, re.S | re.M)
            chunk = m.group(1) if m else content
            arr = _parse_24_ints_from_text(chunk)
            if arr is not None:
                status[name] = {"states": arr}

    # Ensure all appliances exist
    for a in APPLIANCES:
        if a not in status or len(status[a].get("states", [])) != 24:
            print(f"[STATUS] missing/invalid block for {a} → defaulting to zeros.")
            status[a] = {"states": [0]*24}

    return status


def get_mqtt_power_data(timeout: int = 5):
    """Fetch one MQTT TOU JSON."""
    result = {}

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe(MQTT_TOPIC)
        else:
            result["error"] = f"Failed to connect, return code: {rc}"

    def on_message(client, userdata, msg):
        result["payload"] = msg.payload.decode(errors="replace")
        client.disconnect()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    for _ in range(timeout):
        if "payload" in result or "error" in result:
            break
        time.sleep(1)
    client.loop_stop()
    return result.get("payload", result.get("error", "No data received"))


def write_output(schedules):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("Optimised Appliance Schedules (24-hour ON/OFF)\n\n")
        for name in APPLIANCES:
            arr = schedules.get(name, [])
            if len(arr) != 24:
                raise ValueError(f"{name} does not have exactly 24 states.")
            f.write(f"--- {name} ---\n")
            f.write("States:\n")
            f.write(",".join(str(x) for x in arr) + "\n\n")
    print(f"✅ Saved schedules → {os.path.abspath(OUTPUT_FILE)}")

# ---------- Time/Band utils ----------
def fix_length(arr):
    arr = [int(x) & 1 for x in list(arr)]
    if len(arr) < 24:
        arr += [0] * (24 - len(arr))
    elif len(arr) > 24:
        arr = arr[:24]
    return arr

def time_range_to_hours(start_time: str, end_time: str) -> list:
    fmt = "%H:%M"
    s = datetime.strptime(start_time, fmt)
    e = datetime.strptime(end_time, fmt)
    start, end = s.hour, e.hour
    hours, h = [], start
    while True:
        hours.append(h)
        h = (h + 1) % 24
        if h == end:
            break
    return sorted(set(hours))

def extract_first_array(text):
    text = re.sub(r"```[\w\W]*?```", "", text)
    m = re.search(r"\[\s*(?:[01]\s*,\s*)*[01]\s*\]", text, re.S)
    return m.group(0) if m else None

def validate_binary_24(arr, expected_ones=None):
    if not isinstance(arr, list):
        return False
    if len(arr) != 24 or any(x not in (0, 1) for x in arr):
        return False
    if expected_ones is not None and sum(arr) != expected_ones:
        return False
    return True

def parse_user_preferences(user_msg: str):
    allow_peak = {}
    for appliance in APPLIANCES:
        pattern = rf"Allow {re.escape(appliance)} ON during peak hours"
        allow_peak[appliance] = bool(re.search(pattern, user_msg, re.IGNORECASE))
    return allow_peak

# ---------- Post-processing ----------
def redistribute_peak_violations(schedules, tou_json, allow_peak):
    peak_hours = set(tou_json["peak"]["hours"])
    off_peak_hours = tou_json["off_peak"]["hours"]
    day_hours = tou_json["day"]["hours"]

    for appliance, arr in schedules.items():
        if allow_peak.get(appliance, False):
            continue
        removed = 0
        for h in peak_hours:
            if arr[h] == 1:
                arr[h] = 0
                removed += 1

        if removed == 0:
            continue

        def fill(slots, need):
            c = 0
            for h in slots:
                if h in peak_hours:
                    continue
                if arr[h] == 0:
                    arr[h] = 1
                    c += 1
                    if c == need:
                        break
            return c

        filled = fill(off_peak_hours, removed)
        if filled < removed:
            filled += fill(day_hours, removed - filled)
        if filled < removed:
            filled += fill([h for h in range(24) if h not in peak_hours], removed - filled)
        schedules[appliance] = arr
    return schedules

def enforce_required_ons(schedules, tou_json, required_ons, allow_peak):
    peak = set(tou_json["peak"]["hours"])
    offp = [h for h in tou_json["off_peak"]["hours"]]
    day  = [h for h in tou_json["day"]["hours"] if h not in peak and h not in offp]

    for appliance, arr in schedules.items():
        need = required_ons.get(appliance, sum(arr))
        a = arr[:]
        have = sum(a)
        if have == need:
            schedules[appliance] = a
            continue

        if have > need:
            removal_order = []
            if not allow_peak.get(appliance, False):
                removal_order += [h for h in range(24) if h in peak and a[h] == 1]
            removal_order += [h for h in day if a[h] == 1]
            removal_order += [h for h in offp if a[h] == 1]
            for h in removal_order:
                if sum(a) <= need:
                    break
                a[h] = 0
        else:
            add_slots = offp + day
            if allow_peak.get(appliance, False):
                add_slots += [h for h in range(24) if h in peak]
            for h in add_slots:
                if sum(a) >= need:
                    break
                if a[h] == 0:
                    a[h] = 1
        schedules[appliance] = a
    return schedules

# ---------- Deterministic fallback ----------
def optimize_schedule_deterministic(original, tou_json, peak_allowed=False):
    original = fix_length(original)
    total_ones = sum(original)
    arr = original[:]

    peak = set(tou_json["peak"]["hours"])
    offp = [h for h in tou_json["off_peak"]["hours"]]
    day  = [h for h in tou_json["day"]["hours"] if h not in peak and h not in offp]

    if not peak_allowed:
        for h in peak:
            if arr[h] == 1:
                arr[h] = 0
    need = total_ones - sum(arr)
    if need <= 0:
        return arr

    slots = offp + day + (list(peak) if peak_allowed else [])
    for h in slots:
        if need == 0:
            break
        if arr[h] == 0 and (peak_allowed or h not in peak):
            arr[h] = 1
            need -= 1
    if need > 0:
        for h in range(24):
            if need == 0:
                break
            if h in peak and not peak_allowed:
                continue
            if arr[h] == 0:
                arr[h] = 1
                need -= 1
    return arr

# ---------- LLM prompt & call ----------
def build_system_prompt(appliance, original, tou_json, allow_peak, enforced_ones):
    allow_str = (
        "Peak hours are permitted for this appliance ONLY if there are not enough OFF_PEAK and DAY slots.\n"
        if allow_peak else
        "Peak hours are FORBIDDEN for this appliance.\n"
    )
    prompt = (
        "You are a deterministic scheduler. Produce EXACTLY a Python list of 24 integers (0 or 1).\n"
        f"Appliance: {appliance}\n"
        f"Original states (0=OFF,1=ON): {original}\n"
        "Hard constraints:\n"
        "  • Output length = 24.\n"
        f"  • Sum of elements = {enforced_ones} (exactly this many 1s).\n"
        "Time bands (hour indices):\n"
        f"  • DAY      = {tou_json['day']['hours']}\n"
        f"  • PEAK     = {tou_json['peak']['hours']}\n"
        f"  • OFF_PEAK = {tou_json['off_peak']['hours']}\n"
        f"  • {allow_str}"
        "Optimization priorities (in order):\n"
        "  1) Place as many 1s as possible in OFF_PEAK.\n"
        "  2) If OFF_PEAK is full, place remaining 1s in DAY.\n"
        "  3) Only use PEAK if (and only if) allowed and still needed.\n"
        "  4) Prefer grouping 1s contiguously rather than isolated singles.\n"
        "Output format:\n"
        "  Return ONLY a bare Python list of 24 zeros/ones, no text, no code fences.\n"
    )
    return prompt

def schedule_with_llm(llm, appliance, original, tou_json, allow_peak, enforced_ones):
    sys_prompt = build_system_prompt(appliance, original, tou_json, allow_peak, enforced_ones)
    user_msg = "Output ONLY the Python list of 24 integers (0 or 1). No explanations or extra text."

    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            resp = llm.invoke([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_msg},
            ])
            out = getattr(resp, "content", str(resp))
        except Exception as e:
            print(f"LLM error on attempt {attempt}: {e}")
            if attempt < LLM_MAX_RETRIES:
                time.sleep(LLM_RETRY_SECS)
                continue
            out = None

        if not out:
            continue

        print(f"\n========== AI MESSAGE ({appliance}) ==========")
        print(out)
        print("==============================================\n")

        text_arr = extract_first_array(out)
        if not text_arr:
            print("LLM returned no parsable list; retrying...")
            if attempt < LLM_MAX_RETRIES:
                time.sleep(LLM_RETRY_SECS)
                continue
            break

        try:
            arr = ast.literal_eval(text_arr)
            arr = fix_length(arr)
            if not validate_binary_24(arr, expected_ones=enforced_ones):
                raise ValueError("Invalid arr length/values/sum")
            return arr
        except Exception as e:
            print(f"Parse/validate error: {e}; retrying...")
            if attempt < LLM_MAX_RETRIES:
                time.sleep(LLM_RETRY_SECS)
                continue

    print(f"⚠️ Falling back to deterministic schedule for {appliance}")
    # build a temporary vector with `enforced_ones` ones (use original as base)
    tmp = original[:]
    # If original has fewer/more ones than enforced_ones, adjust minimally
    diff = enforced_ones - sum(tmp)
    if diff > 0:
        for i in range(24):
            if tmp[i] == 0:
                tmp[i] = 1
                diff -= 1
                if diff == 0:
                    break
    elif diff < 0:
        for i in range(24):
            if tmp[i] == 1:
                tmp[i] = 0
                diff += 1
                if diff == 0:
                    break
    return optimize_schedule_deterministic(tmp, tou_json, peak_allowed=allow_peak)

# ---------- Main ----------
def main_once():
    if GENERATE_DEMO_FILE:
        _write_demo_status_file(STATUS_FILE)

    # 1) Load predicted on/off states
    status = read_appliance_status(STATUS_FILE)
    all_zero = True
    for a in APPLIANCES:
        arr = status.get(a, {}).get("states", [0]*24)
        s = sum(arr)
        print(f"[STATUS] {a}: sum={s} len={len(arr)} head={arr[:8]}")
        all_zero &= (s == 0)
    if all_zero:
        print("⚠️  All appliances are zero. LLM will still be invoked (sum may be lifted by MIN_ONS if configured).")

    # 2) TOU JSON
    tou_json_raw = get_mqtt_power_data()
    try:
        tou_json = json.loads(tou_json_raw)
    except Exception as e:
        print("Failed to parse TOU JSON from MQTT:", e)
        print("Raw payload:", tou_json_raw)
        tou_json = {
            "day":      {"time": "06:00 - 18:00"},
            "peak":     {"time": "18:00 - 22:00"},
            "off_peak": {"time": "22:00 - 06:00"},
        }

    for period, values in tou_json.items():
        start, end = values["time"].replace("–", "-").split("-")
        start = start.strip()
        end   = end.strip()
        tou_json[period]["hours"] = time_range_to_hours(start, end)
        print(f"Period {period} covers hours: {tou_json[period]['hours']}")

    # 3) User preferences (hardcode or wire to UI)
    user_msg = "Allow AC_Power ON during peak hours"
    allow_peak = parse_user_preferences(user_msg)

    # 4) Init LLM (required for LLM-first design)
    if not HAS_OLLAMA:
        print("❌ Ollama/ChatOllama not available but LLM is required. Install/pull model or set HAS_OLLAMA.")
    llm = ChatOllama(model=LLM_MODEL, temperature=LLM_TEMPERATURE) if HAS_OLLAMA else None

    # 5) LLM-first scheduling
    schedules = {}
    required_ons = {}

    for appliance in APPLIANCES:
        original = status.get(appliance, {}).get("states", [0]*24)
        original = fix_length(original)
        predicted_ones = sum(original)

        # lift by MIN_ONS if configured
        enforced_ones = max(predicted_ones, int(MIN_ONS.get(appliance, 0)))
        required_ons[appliance] = enforced_ones

        if llm is None:
            print(f"⚠️ No LLM available for {appliance}; using deterministic fallback.")
            # adjust original to enforced_ones, then optimize
            tmp = original[:]
            diff = enforced_ones - sum(tmp)
            if diff > 0:
                for i in range(24):
                    if tmp[i] == 0:
                        tmp[i] = 1
                        diff -= 1
                        if diff == 0:
                            break
            elif diff < 0:
                for i in range(24):
                    if tmp[i] == 1:
                        tmp[i] = 0
                        diff += 1
                        if diff == 0:
                            break
            arr = optimize_schedule_deterministic(tmp, tou_json, peak_allowed=allow_peak.get(appliance, False))
        else:
            arr = schedule_with_llm(llm, appliance, original, tou_json, allow_peak.get(appliance, False), enforced_ones)

        schedules[appliance] = arr

    # 6) Post-process across appliances (safety)
    schedules = redistribute_peak_violations(schedules, tou_json, allow_peak)
    schedules = enforce_required_ons(schedules, tou_json, required_ons, allow_peak)

    # 7) Final validation & save
    for a in APPLIANCES:
        arr = schedules[a]
        assert len(arr) == 24, f"{a} does not have 24 elements"
        assert all(v in (0, 1) for v in arr), f"{a} contains non-binary values"
        if not allow_peak.get(a, False):
            assert all(arr[i] == 0 for i in tou_json["peak"]["hours"]), f"{a} ON during forbidden peak hour"
        print(f"{a} final ON count: {sum(arr)}")

    write_output(schedules)


if __name__ == "__main__":
    if RUN_ONCE:
        main_once()
    else:
        while True:
            main_once()
            print(f"Waiting {RUN_INTERVAL_SECS} seconds for next run...")
            time.sleep(RUN_INTERVAL_SECS)
