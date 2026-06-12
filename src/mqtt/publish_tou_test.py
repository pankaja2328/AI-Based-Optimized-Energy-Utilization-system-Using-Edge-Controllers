import time
import requests
from bs4 import BeautifulSoup
import paho.mqtt.client as mqtt
import json

while True:
    try:
        # -- 1. Scrape the page --
        url = "https://www.leco.lk/pages_e.php?id=86"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table", class_="table")
        if not table:
            raise Exception("Could not find table with TOU data!")

        tou_found = False
        tou_data = {}
        rows = table.find_all("tr")

        for i, row in enumerate(rows):
            cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if not cols:
                continue
            if "Domestic – Optional Time of Use Tariff" in cols[0]:
                tou_found = True
                continue
            if tou_found and ("Day(" in cols[0] or "Peak" in cols[0] or "Off-peak" in cols[0]):
                label = None
                time_range = None
                rate = None

                if "Day(" in cols[0]:
                    label = "day"
                    time_range = cols[0].split("(")[1].split(")")[0].replace("hours", "").strip()
                elif "Peak" in cols[0]:
                    label = "peak"
                    time_range = cols[0].split("(")[1].split(")")[0].replace("hours", "").strip()
                elif "Off-peak" in cols[0]:
                    label = "off_peak"
                    time_range = cols[0].split("(")[1].split(")")[0].replace("hours", "").strip()
                    for dash in ['\u2013', '\u2014', '–', '—']:
                        time_range = time_range.replace(dash, '-')

                try:
                    rate = float(cols[1].replace(",", ""))
                except:
                    rate = None

                tou_data[label] = {
                    "rate": rate,
                    "time": time_range
                }
            elif tou_found and not ("Day(" in cols[0] or "Peak" in cols[0] or "Off-peak" in cols[0]):
                break

        print("TOU rates and times extracted:", tou_data)

        # -- 2. Publish to test.mosquitto.org --
        MQTT_BROKER = "test.mosquitto.org"
        MQTT_PORT = 1883
        MQTT_TOPIC = "power/tou_domestic"

        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 60)

        payload = json.dumps(tou_data)
        print(f"Publishing TOU data: {payload}")
        client.publish(MQTT_TOPIC, payload=payload, qos=1, retain=True)
        print(f"Published TOU data to MQTT topic {MQTT_TOPIC}: {payload}")

        client.disconnect()

    except Exception as e:
        print("Error:", e)

    print("Waiting 5 minutes before next update...\n")
    time.sleep(300)
