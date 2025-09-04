import paho.mqtt.client as mqtt
import time
import ast
import json
from langchain_ollama import ChatOllama
import ollama
from datetime import datetime, timedelta
import re

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
#MQTT_USER = "malshan"
#MQTT_PASS = "Pankaja1"
MQTT_TOPIC = "power/tou_domestic"
APPLIANCES = [
    'WashingMachine_Power',
    'Heater_Power',
    'AC_Power',
    'VehicleCharger_Power',
    'VacuumCleaner_Power'
]

def get_mqtt_power_data(timeout: int = 5):
    """
    Fetch one MQTT message (TOU rates) as string payload from the broker.
    """
    result = {}
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC)
        else:
            result['error'] = f"Failed to connect, return code: {rc}"
    def on_message(client, userdata, msg):
        result['payload'] = msg.payload.decode()
        client.disconnect()
    client = mqtt.Client()
    #client.username_pw_set(MQTT_USER, MQTT_PASS)
    #client.tls_set()
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

def read_appliance_status(filename: str):
    """
    Parse appliance status file to extract ON/OFF sequences for each appliance.
    """
    status = {}
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
        elif line == "States:" and current_appliance:
            i += 1
            status[current_appliance]["states"] = [int(x.strip()) for x in lines[i].split(",") if x.strip()]
            i += 1
        else:
            i += 1
    return status

def write_output(schedules):
    """
    Write the optimized 24-hour ON/OFF schedule for each appliance to output.txt.
    """
    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write("Optimised Appliance Schedules (24-hour ON/OFF)\n\n")
        for name in APPLIANCES:
            arr = schedules.get(name, [])
            if len(arr) != 24:
                raise ValueError(f"{name} does not have exactly 24 states.")
            f.write(f"--- {name} ---\n")
            f.write(f"States: {arr}\n\n")
    print("Optimised ON/OFF schedules saved to output.txt")

def fix_length(arr):
    """
    Ensure ON/OFF array has exactly 24 values (pads/truncates as needed).
    """
    arr = list(arr)
    if len(arr) < 24:
        arr = arr + [0] * (24 - len(arr))
    if len(arr) > 24:
        arr = arr[:24]
    return arr

def time_range_to_hours(start_time: str, end_time: str) -> list:
    """
    Convert time range strings (e.g. '05:00', '18:00') into a list of hour indices.
    """
    fmt = "%H:%M"
    start = datetime.strptime(start_time, fmt)
    end = datetime.strptime(end_time, fmt)
    hours = []
    current = start
    while True:
        hours.append(current.hour)
        current += timedelta(hours=1)
        if current.hour == end.hour:
            break
        if current.hour == start.hour and current.minute == start.minute:
            break  # safety
    return sorted(set(hours))

def extract_first_dict(text):
    """
    Extract the first {...} block from LLM output (no markdown, just the dict).
    """
    text = re.sub(r"```[\w\s]*", "", text)
    stack = []
    start = None
    for i, c in enumerate(text):
        if c == '{':
            if not stack:
                start = i  # <-- fixed typo!
            stack.append(c)
        elif c == '}':
            if stack:
                stack.pop()
                if not stack and start is not None:
                    return text[start:i+1]
    return None

def extract_first_array(text):
    """
    Extract the first [...] block from LLM output (no markdown, just the array).
    """
    text = re.sub(r"```[\w\s]*", "", text)  # strip code fences
    m = re.search(r"\[[^\[\]]{1,200}\]", text, re.S)
    return m.group(0) if m else None

def redistribute_peak_violations(schedules, tou_json, allow_peak):
    """
    For each appliance, ensures no ONs in peak hours.
    All ONs in PEAK are removed and redistributed to OFF-PEAK (preferred), then DAY hours.
    If not enough slots, puts ONs in first available non-peak slots.
    Returns fully "legalized" schedules.
    """
    for appliance, arr in schedules.items():
        if allow_peak.get(appliance, False):
            continue  # Skip enforcement for this appliance

        peak_hours = tou_json["peak"]["hours"]
        off_peak_hours = tou_json["off_peak"]["hours"]
        day_hours = tou_json["day"]["hours"]

        # 1. Remove all ONs in peak hours, remember how many
        removed_on_count = 0
        for h in peak_hours:
            if arr[h] == 1:
                removed_on_count += 1
                arr[h] = 0

        # 2. Total ONs that must be present (after LLM output)
        total_on = sum(arr) + removed_on_count

        # 3. Redistribute: Fill OFF-PEAK hours first, then DAY hours, then anywhere else
        filled = sum(arr)
        for hour_list in [off_peak_hours, day_hours, range(24)]:
            for h in hour_list:
                if arr[h] == 0 and h not in peak_hours and filled < total_on:
                    arr[h] = 1
                    filled += 1
            if filled >= total_on:
                break

        schedules[appliance]
    return schedules

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

def enforce_required_ons(schedules, tou_json, required_ons):
    peak_hours = set(tou_json["peak"]["hours"])
    off_peak_hours = [h for h in tou_json["off_peak"]["hours"]]
    day_hours = [h for h in tou_json["day"]["hours"] if h not in peak_hours and h not in off_peak_hours]
    for appliance, arr in schedules.items():
        arr = [0]*24
        needed = required_ons.get(appliance, 0)
        # Fill off-peak first
        for h in off_peak_hours[:needed]:
            arr[h] = 1
        left = needed - min(needed, len(off_peak_hours))
        # Fill remaining in day hours if needed
        if left > 0:
            for h in day_hours[:left]:
                arr[h] = 1
        schedules[appliance] = arr
    return schedules

def parse_user_preferences(user_msg):
    """
    Returns a dict: {appliance_name: allow_peak (True/False)}
    Example: "Allow AC_Power ON during peak hours"
    """
    allow_peak = {}
    for appliance in APPLIANCES:
        # Look for phrases like "Allow AC_Power ON during peak hours"
        pattern = rf"Allow {appliance} ON during peak hours"
        if re.search(pattern, user_msg, re.IGNORECASE):
            allow_peak[appliance] = True
        else:
            allow_peak[appliance] = False
    return allow_peak

def main_loop():
    status = read_appliance_status("appliance_data.txt")
    tou_json_raw = get_mqtt_power_data()
    weather = {
        "temperature": [25, 24, 23, 22, 22, 23, 24, 25, 26, 27, 28, 29, 30, 30, 29, 28, 27, 26, 25, 24, 23, 22, 22, 23],
        "humidity": [60, 62, 65, 67, 70, 72, 75, 77, 80, 82, 85, 87, 90, 92, 95, 97, 100, 102, 105, 107, 110, 112, 115, 117]
    }
    try:
        tou_json = json.loads(tou_json_raw)
    except Exception as e:
        print("Failed to parse TOU JSON from MQTT:", e)
        print("Raw payload:", tou_json_raw)
        return

    for period, values in tou_json.items():
        start, end = values["time"].split(" - ")
        tou_json[period]["hours"] = time_range_to_hours(start, end)
        print(f"Period {period} covers hours: {tou_json[period]['hours']}")

    # Hardcoded user preferences for now
    user_msg = "Allow AC_Power ON during peak hours"
    allow_peak = parse_user_preferences(user_msg)

    llm = ChatOllama(model="llama3.2:latest", temperature=0.0)
    #llm = ChatOllama(model="mistral:7b")
    schedules = {}
    required_ons = {}
    # Loop over appliances
    for i, appliance in enumerate(APPLIANCES):
        sys_prompt = build_system_prompt(APPLIANCES, status, tou_json, weather, i, allow_peak)
        user_msg = (
            "Output ONLY the Python array for this appliance. "
            "No explanations, no markdown, no code blocks, no latex, no extra text."
        )
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = llm.invoke([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_msg}
                ])
                out = response.content
                break
            except ollama._types.ResponseError as e:
                print(f"Ollama error: {e}. Retrying in 60 seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(60)
            except Exception as e:
                print(f"Unexpected error: {e}. Retrying in 60 seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(60)
        else:
            print(f"Failed to get response from LLM for {appliance} after several attempts.")
            schedules[appliance] = [0]*24
            continue

        print(f"\n========== AI MESSAGE ({appliance}) ==========")
        print(out)
        print("==============================================\n")
        # Parse and post-process
        try:
            dict_text = extract_first_array(out)
            if dict_text is None:
                raise ValueError("No list found in LLM output.")
            arr = ast.literal_eval(dict_text)         # converts '[0,1,…]' to list
            arr = fix_length(arr)
            arr = [int(x) & 1 for x in arr]           # force 0/1
            # Post-process: remove peak ONs and enforce required ONs
            required_ons[appliance] = sum(status.get(appliance, {}).get("states", []))
            schedules[appliance] = arr
        except Exception as e:
            print(f"LLM output for {appliance} could not be parsed. Error: {e}")
            schedules[appliance] = [0]*24

    # Post-process all schedules together
    schedules = redistribute_peak_violations(schedules, tou_json, allow_peak)
    schedules = enforce_required_ons(schedules, tou_json, required_ons)

    # Final validation and output
    for a in APPLIANCES:
        arr = schedules[a]
        assert len(arr) == 24, f"{a} does not have 24 elements"
        assert all(v in [0, 1] for v in arr), f"{a} contains non-binary values"
        assert all(arr[i] == 0 for i in tou_json["peak"]["hours"]), f"{a} ON during peak hour"
    write_output(schedules)
    for appliance, arr in schedules.items():
        for h in tou_json["peak"]["hours"]:
            if arr[h] == 1:
                print(f"{appliance} ON during forbidden peak hour {h}")
        print(f"{appliance} final ON count: {sum(arr)}")

if __name__ == "__main__":
    while True:
        main_loop()
        print("Waiting 30 minutes for next run...")
        time.sleep(1800)
