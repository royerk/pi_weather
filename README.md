# pi_weather

This is a simple weather station that uses a Raspberry Pi and a BME280 sensor to measure temperature, humidity, and pressure. The data is then sent to a web server.

## Installation - Server

todo: use make to `scp` + load env vars for credentials

## Installation - Sensor

todo: use make to `scp` + load env vars for credentials

## Local Development

- Raspbian has `python3.9`, docker images use `python3.10`
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

todo: docker/make local server + tests
