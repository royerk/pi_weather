# pi_weather

This is a simple weather station that uses a Raspberry Pi and a BMP280 sensor to measure temperature, ~~humidity~~, and pressure. The data is then sent to a web server.

To do:

- sensor retry

## Installation - Server

- `make safe-delete-server-remote`: copy `weather_data.db` then delete all code and data
- `make deploy`: move and expand code to server
- `make setup-server-remote`: install dependencies, setup db
- `make run-server-remote`: start server, add cronjob to start server on boot
- (`make stop-server-remote`: stop server, remove cronjob to start server on boot)

## Installation - Sensor

- BMP280-3.3
- `make deploy-sensor-2`
- `make clean-sensor-2`

## Local Development

- note: raspbian has `python3.9`, docker images use `python3.10`
- `make test`: run container and tests
- `make lint`: isort/black/mdformat
- curl

```bash
curl -X POST -H "Content-Type: application/json" -d '{
    "device_name": "your_device_name",
    "temperature": 20.0,
    "humidity": 50.0,
    "pressure": 1013.25,
    "date": "2024-03-01 00:00:0"
}' http://172.17.0.2:5000/v1/data_point/add
```

```bash
curl "http://172.17.0.2:5000/v1/data_point/last_day?device_name=your_device_name"
```

```bash
curl -X POST -H "Content-Type: application/json" -d '{
    "device_name": "toto device",
    "alias": "toto alias"
    }' http://172.17.0.2:5000/v1/alias
```