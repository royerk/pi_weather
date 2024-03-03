import base64
import io
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict

import matplotlib.pyplot as plt
from db_utils import DB_FILE
from flask import Flask, jsonify, request
from matplotlib.dates import DateFormatter, HourLocator

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


@app.route("/")
def index():
    return "Hello world"


@app.route("/v1/data_point/add", methods=["POST"])
def add_data_point():
    data = request.json

    device_name = data.get("device_name")
    temperature = data.get("temperature")
    humidity = data.get("humidity")
    pressure = data.get("pressure")
    date = data.get("date")

    if None in [device_name, temperature, humidity, pressure, date]:
        return jsonify({"message": "Missing data"}), 400

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO sensor_data (device_name, temperature, humidity, pressure, date)
                VALUES (?, ?, ?, ?, ?);""",
                (device_name, temperature, humidity, pressure, date),
            )
            conn.commit()
    except sqlite3.Error as e:
        return jsonify({"message": "Database error: {}".format(e)}), 500

    return jsonify({"message": "Data received successfully"}), 200


@app.route("/v1/data_point/last_day", methods=["GET"])
def get_last_day_data():
    device_name = request.args.get("device_name")

    if not device_name:
        return jsonify({"message": "Missing device name"}), 400

    columns = ["temperature", "humidity", "pressure", "date"]
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            query = f"""
                SELECT {", ".join(columns)}
                FROM sensor_data
                WHERE device_name = ?
                AND date >= datetime('now', '-1 day')
            """
            cursor.execute(query, (device_name,))
            rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({column: row[i] for i, column in enumerate(columns)})
    except sqlite3.Error as e:
        return jsonify({"message": "Database error: {}".format(e)}), 500

    return jsonify(data), 200


def get_graphs() -> Dict[str, Dict]:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            query = """
                SELECT device_name, temperature, humidity, pressure, date
                FROM sensor_data
                WHERE date >= ?
                ORDER BY date;
            """
            start_time = datetime.now() - timedelta(days=1)
            cursor.execute(query, (start_time,))
            rows = cursor.fetchall()

        devices = {}
        for row in rows:
            device_name = row[0]
            if device_name not in devices:
                devices[device_name] = {
                    "temperature": [],
                    "humidity": [],
                    "pressure": [],
                    "date": [],
                }
            devices[device_name]["temperature"].append(row[1])
            devices[device_name]["humidity"].append(row[2])
            devices[device_name]["pressure"].append(row[3])
            devices[device_name]["date"].append(
                datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S")
            )

        plot_images = {}
        for device_name, data in devices.items():
            plot_images[device_name] = {}
            for metric in ["temperature", "pressure"]:
                plt.figure(figsize=(10, 6))
                plt.plot(data["date"], [float(x) for x in data[metric]], label=metric)
                plt.gca().xaxis.set_major_locator(HourLocator())
                plt.gca().xaxis.set_major_formatter(DateFormatter("%H"))
                plt.xticks(rotation=45)
                plt.grid()
                plt.xlabel("Date")
                plt.title(f"{metric} for {device_name}")
                plt.legend()

                img_bytes = io.BytesIO()
                plt.savefig(img_bytes, format="png")
                img_bytes.seek(0)

                img_base64 = base64.b64encode(img_bytes.getvalue()).decode()
                plot_images[device_name][metric] = img_base64

                plt.close()

        return plot_images
    except sqlite3.Error as e:
        logging.error(f"get_graphs, error: {e}")
        return {}


@app.route("/latest_data")
def latest_data():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            query = """
                SELECT s1.device_name,
                    s1.temperature,
                    s1.humidity,
                    s1.pressure,
                    s1.date
                FROM sensor_data s1
                JOIN (
                    SELECT device_name, MAX(date) AS max_date
                    FROM sensor_data
                    GROUP BY device_name
                ) s2
                ON s1.device_name = s2.device_name AND s1.date = s2.max_date;
            """
            cursor.execute(query)
            rows = cursor.fetchall()

        html_content = "<h1>Latest Data for Each Device</h1>"
        html_content += '<table border="1">'
        html_content += "<tr><th>Device Name</th><th>Temperature</th><th>Humidity</th><th>Pressure</th><th>Date</th></tr>"
        for row in rows:
            html_content += f"<tr><td>{row[0]}</td><td>{row[1]:.1f}</td><td>{row[2]:.1f}</td><td>{row[3]:.1f}</td><td>{row[4]}</td></tr>"
        html_content += "</table>"

        images_dict = get_graphs()

        html_content += "<h1>Last 24h</h1>"
        for row in rows:
            device_name = row[0]
            for metric in ["temperature", "pressure"]:
                img_base64 = images_dict[device_name][metric]
                html_content += f"<img src='data:image/png;base64,{img_base64}'><br>"

        return html_content
    except sqlite3.Error as e:
        return f"Error: {e}"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
