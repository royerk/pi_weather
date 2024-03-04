import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()

REMOTE_PATH = os.getenv("REMOTE_PATH")

DB_FILE = os.path.join(REMOTE_PATH, "weather_data.db")

if os.environ.get("IS_DOCKER"):
    DB_FILE = "weather_data.db"


def datetime_to_string(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def initialize_database():
    if not os.path.exists(DB_FILE):
        try:
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
        except sqlite3.OperationalError as e:
            print(f"Error: {e}, {DB_FILE=}")
    else:
        print(f"Database already exists: {DB_FILE}")


if __name__ == "__main__":
    initialize_database()
