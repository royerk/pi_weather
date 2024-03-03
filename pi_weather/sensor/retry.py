import json
import os

import requests
from sensor import MISSED_LOGS_DIR, SERVER_URL

for file in os.listdir(MISSED_LOGS_DIR):
    with open(f"{MISSED_LOGS_DIR}/{file}") as f:
        data = json.load(f)
    response = requests.post(f"{SERVER_URL}/v1/data_point/add", json=data)
    if response.status_code == 200:
        os.remove(f"{MISSED_LOGS_DIR}/{file}")
