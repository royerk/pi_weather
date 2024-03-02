import json
import os
import socket
from datetime import datetime

from bmp280 import BMP280
from dotenv import load_dotenv

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

import requests

load_dotenv()


def create_if_not_exists(directory: str) -> None:
    if not os.path.exists(directory):
        os.makedirs(directory)


REMOTE_HOST = os.getenv("REMOTE_HOST")
SERVER_URL = f"http://{REMOTE_HOST}:5000"
MISSED_LOGS_DIR = "missed_logs"

bus = SMBus(1)
bmp280 = BMP280(i2c_dev=bus)

temperature = bmp280.get_temperature()
pressure = bmp280.get_pressure()

data = {
    "device_name": socket.gethostname(),
    "temperature": temperature,
    "pressure": pressure,
    "humidity": 0,
    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}

response = requests.post(f"{SERVER_URL}/v1/data_point/add", json=data)

if response.status_code != 200:
    create_if_not_exists(MISSED_LOGS_DIR)
    with open(
        f"{MISSED_LOGS_DIR}/{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.json", "w"
    ) as f:
        json.dump(data, f)
