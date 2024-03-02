import subprocess
import time
from datetime import datetime, timedelta

import pytest
import requests

from pi_weather.app.db_utils import datetime_to_string


@pytest.fixture(scope="module")
def test_container():
    container_id = (
        subprocess.check_output(
            ["docker", "run", "--rm", "-d", "-p", "5000:5000", "pi-weather"]
        )
        .decode()
        .strip()
    )
    time.sleep(4)
    yield container_id
    subprocess.run(["docker", "stop", container_id])


@pytest.fixture(scope="module")
def get_ip_address(test_container):
    container_id = test_container
    ip_address = (
        subprocess.check_output(
            [
                "docker",
                "inspect",
                "-f",
                "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
                container_id,
            ]
        )
        .decode()
        .strip()
    )
    return ip_address


def test_application_runs(get_ip_address):
    ip_address = get_ip_address
    device_name = "test_device"
    current_time = datetime.now()
    n_data_points = 10
    for hour in range(n_data_points):
        data = {
            "device_name": device_name,
            "temperature": 20.0,
            "humidity": 50.0,
            "pressure": 1013.25,
            "date": datetime_to_string(current_time - timedelta(hours=hour)),
        }
        response = requests.post(
            f"http://{ip_address}:5000/v1/data_point/add", json=data
        )
        assert response.status_code == 200, "Post request failed"

    response = requests.get(
        f"http://{ip_address}:5000/v1/data_point/last_day?device_name={device_name}"
    )

    assert response.status_code == 200, f"Get request failed"
    data = response.json()
    assert len(data) == n_data_points, "Incorrect number of data points returned"
