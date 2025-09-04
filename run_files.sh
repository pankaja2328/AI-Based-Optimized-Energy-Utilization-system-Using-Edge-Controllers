#!/bin/bash

# --- MQTT Publisher ---
sudo systemctl start mosquitto
echo "[+] Starting MQTT Publisher script..."
(
    source /home/pankaja/Desktop/LLAMA/LangGraph/bin/activate
    python3 test_publish.py
    deactivate
    echo "[✓] MQTT Publisher finished."
) &

# --- Delay before starting next script ---
sleep 10

# --- LSTM Predictor ---
echo "[+] Starting LSTM Predictor script..."
(
    source /home/pankaja/Desktop/Research/AI-Based-Optimized-Energy-Utilization-System-Using-Edge-Computing-Controller-main/tf-env/bin/activate
    python3 Run_LSTM.py
    deactivate
    echo "[✓] LSTM Predictor finished."
) &

# --- Delay before starting next script ---
sleep 10

# --- LLM Agent ---
echo "[+] Starting LLM Agent script..."
(
    source /home/pankaja/Desktop/LLAMA/LangGraph/bin/activate
    python3 copy_research_agent.py
    deactivate
    echo "[✓] LLM Agent finished."
) &



echo ""
echo "------------------------------------"
echo "[✓] All scripts executed in parallel with 10-second delays."
echo "------------------------------------"
echo "HTTP Server is running on port 8000."
echo "------------------------------------"
python3 -m http.server 8000 --directory /home/pankaja/Desktop/Research/External
echo "------------------------------------"
echo "[✓] HTTP Server finished."
echo "------------------------------------"

# --- Wait for all background jobs ---
wait