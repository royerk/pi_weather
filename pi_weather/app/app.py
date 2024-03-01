import sqlite3

from flask import Flask, jsonify, request
from init_db import DB_FILE

app = Flask(__name__)


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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
