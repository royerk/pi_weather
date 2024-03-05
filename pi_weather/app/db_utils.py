import logging
import os
import sqlite3
from typing import Dict

from dotenv import load_dotenv

load_dotenv()

REMOTE_PATH = os.getenv("REMOTE_PATH")

DB_FILE = os.path.join(REMOTE_PATH, "weather_data.db")

if os.environ.get("IS_DOCKER"):
    DB_FILE = "weather_data.db"


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
