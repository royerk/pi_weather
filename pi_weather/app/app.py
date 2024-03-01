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
                VALUES (?, ?, ?, ?, ?)""",
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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
