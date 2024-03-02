import logging
import sqlite3

from db_utils import DB_FILE
from flask import Flask, jsonify, request

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)


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

    if not all([device_name, temperature, humidity, pressure, date]):
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

        conn.close()

        html_content = "<h1>Latest Data for Each Device</h1>"
        html_content += '<table border="1">'
        html_content += "<tr><th>Device Name</th><th>Temperature</th><th>Humidity</th><th>Pressure</th><th>Date</th></tr>"
        for row in rows:
            html_content += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>"
        html_content += "</table>"

        return html_content
    except sqlite3.Error as e:
        return f"Error: {e}"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
