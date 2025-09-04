# AI-Based Optimized Energy Utilization (Edge Controller)

Smart home energy scheduler that:
1) reads **Time-of-Use (TOU)** tariffs from MQTT,  
2) takes **appliance ON/OFF predictions** (24-hour arrays),  
3) uses an **AI agent + rule-based post-processing** to shift loads away from expensive bands, and  
4) writes two files:
   - `output.txt` – final 24h ON/OFF schedule per appliance
   - `output_explanations.txt` – reasons for each change + per-appliance and total cost savings

> Designed for edge devices (e.g., Raspberry Pi) and tested on desktop (Python). ROBO mode-friendly and easily swapped to real APIs later.

---

## Features

- **MQTT input** for TOU (topic: `power/tou_domestic`)
- **Supports keys** `rate` / `price` / `tariff` in incoming JSON
- **LLM-assisted scheduling** via [Ollama](https://ollama.com/) (toggle on/off)
- **Hard constraints**: no peak usage unless explicitly allowed per appliance
- **Deterministic cost analysis** (kWh × hourly rate) with human-readable reasons
- **Robust time-band parser** (handles wrap-around like `22:30–05:30`, and `24:00`)

---

## Repository Structure

```

.
├─ ipdated\_agent.py            # Main agent (schedules + reasons + savings)
├─ appliance\_data.txt          # Input: per-appliance 24h ON/OFF predictions
├─ output.txt                  # Output: final schedules (overwritten each run)
└─ output\_explanations.txt     # Output: reasons + costs (overwritten each run)

````

> If you want file **history** instead of overwrites, we can add a `logs/` folder and timestamped copies.

---

## Requirements

- Python 3.10–3.13
- MQTT broker (public test used by default)
- (Optional) Ollama running locally if `USE_LLM_FOR_SCHED=True`

### Python deps
Create a venv and install:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install paho-mqtt langchain-ollama ollama
````

### Ollama (optional, for LLM scheduling)

```bash
# Install Ollama (see https://ollama.com/download)
ollama serve &
ollama pull llama3.2
```

---

## Configuration

Edit these in `ipdated_agent.py`:

```python
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT   = 1883
MQTT_TOPIC  = "power/tou_domestic"

APPLIANCES = [
  "WashingMachine_Power",
  "Heater_Power",
  "AC_Power",
  "VehicleCharger_Power",
  "VacuumCleaner_Power"
]

POWER_KWH = {
  "WashingMachine_Power": 0.6,  # kWh per ON hour
  "Heater_Power":         2.0,
  "AC_Power":             1.2,
  "VehicleCharger_Power": 2.2,
  "VacuumCleaner_Power":  1.1,
}

USE_LLM_FOR_SCHED = True
LLM_MODEL = "llama3.2:latest"
LLM_TEMP  = 0.0
```

> **Tip:** Adjust `POWER_KWH` to match your appliances for accurate savings.

---

## Inputs

### 1) TOU from MQTT (topic `power/tou_domestic`)

**Example payload (exactly what your broker publishes):**

```json
{
  "day":      { "rate": 35.0, "time": "05:30 - 18:30" },
  "peak":     { "rate": 67.0, "time": "18:30 - 22:30" },
  "off_peak": { "rate": 21.0, "time": "22:30 - 05:30" }
}
```

* Keys `rate`/`price`/`tariff` are all accepted.
* Currency defaults to **LKR** if not provided.

> **Time-band semantics:** we treat bands as **half-open** intervals `[start, end)`, rounded down to the hour boundary.
> Example: `05:30–18:30` → hours `[5,6,...,17]`.

### 2) Appliance predictions (`appliance_data.txt`)

Provide 24 ints (0/1) per appliance:

```
--- WashingMachine_Power ---
States:
0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0

--- Heater_Power ---
States:
0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0

--- AC_Power ---
States:
0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0

--- VehicleCharger_Power ---
States:
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0

--- VacuumCleaner_Power ---
States:
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0
```

These can be produced by your **LSTM appliance-level predictor** and written to file before running the agent.

---

## Running

**One-shot test** (single cycle):

```bash
python ipdated_agent.py
```

**Continuous** (every 30 minutes by default; see `main_loop()`):

```bash
python ipdated_agent.py
```

Outputs (overwritten on each successful cycle):

* `output.txt` – final ON/OFF schedule for each appliance (24 values)
* `output_explanations.txt` – band shifts, constraint notes, original vs optimized cost, total savings

---

## How It Works (Quick)

1. **TOU ingest**: Subscribes to MQTT topic and parses bands into hour indices.
2. **Initial schedule**: Starts from your predicted 24h ON/OFF arrays (or asks LLM to rearrange while keeping the **same ON count**).
3. **Rule-based post-process**:

   * Drop ONs in **peak** (unless explicitly allowed per appliance),
   * Fill **off-peak** first, then **day** hours, preserving the total ON count.
4. **Costing & Reasons**:

   * Cost per hour = `rate × kWh_when_ON`.
   * Explains each “move” (e.g., peak→off-peak) and estimates per-appliance + total savings.

---

## Allowing Peak Hours (per appliance)

By default, peak hours are avoided. You can embed a user preference like:

```python
user_msg = "Allow AC_Power ON during peak hours"
```

The agent parses this and allows AC usage in peak if needed (still reported in reasons).

---

## Troubleshooting

* **`KeyError: 'price'`**
  Your payload uses `"rate"`. The script now accepts `rate`/`price`/`tariff`. Make sure the MQTT JSON matches the example above.

* **Paho deprecation warning**
  Harmless. We auto-use v5 callbacks if available; otherwise fall back to v1. You can upgrade `paho-mqtt` or force v5 in code.

* **LLM not responding**
  The agent falls back to the original prediction. Ensure `ollama serve` is running and the model is pulled:
  `ollama pull llama3.2`

* **“No data received”**
  Check broker availability, topic name, and that messages are being published. You can increase the MQTT wait timeout.

---

## Roadmap

* Integrate direct **cost APIs** from power providers.
* Stream **weather** and **indoor sensors** (temp/humidity/occupancy).
* Replace LLM rearrangement with a small **Q-learning** agent for fully local optimization.
* Add **history mode** (timestamped logs) and **Prometheus** metrics.

---


## Acknowledgements

* MQTT via `paho-mqtt`
* LLM scheduling via `langchain-ollama` + `ollama`
* Project goal: **AI-Based Optimized Energy Utilization System Using Edge Computing Controller** (appliance-level LSTM predictions + AI control)
