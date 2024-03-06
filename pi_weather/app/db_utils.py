import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, Union

from dotenv import load_dotenv

load_dotenv()

REMOTE_PATH = os.getenv("REMOTE_PATH")

DB_FILE = os.path.join(REMOTE_PATH, "weather_data.db")

if os.environ.get("IS_DOCKER"):
    DB_FILE = "weather_data.db"


def get_latest_sensor_data() -> Dict[str, Dict[str, Union[float, datetime]]]:
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

    data = {}
    for row in rows:
        device_name = row[0]
        if device_name not in data:
            data[device_name] = {}
        data[device_name]["temperature"] = row[1]
        data[device_name]["humidity"] = row[2]
        data[device_name]["pressure"] = row[3]
        data[device_name]["date"] = datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S")

    return data


def datetime_to_string(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def create_sensor_data_table():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                date DATETIME
            );
        """
        )
        conn.commit()


def get_alias() -> Dict[str, str]:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT device_name, alias FROM alias;")
            rows = cursor.fetchall()

        return {row[0]: row[1] for row in rows}
    except sqlite3.Error as e:
        logging.error(f"get_alias, error: {e}")
        return {}


def create_alias_table():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alias (
                device_name TEXT,
                alias TEXT
            );
        """
        )
        conn.commit()


def initialize_database():
    create_sensor_data_table()
    create_alias_table()


if __name__ == "__main__":
    initialize_database()
