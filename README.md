# pi_weather

This is a simple weather station that uses a Raspberry Pi and a BME280 sensor to measure temperature, ~~humidity~~, and pressure. The data is then sent to a web server.

## Installation - Server

- `make safe-delete-server-remote`: copy `data.db` then delete all code and data
- `make deploy-remote`: move code to server
- `make setup-server-remote`: install dependencies, setup db
- `make run-server-remote`: start server
- (`make stop-server-remote`: stop server)

TODO: start server on boot

## Installation - Sensor

todo: use make to `scp` + load env vars for credentials

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

## BMP280-3.3

```md
To use the BMP280 sensor with a Raspberry Pi operating at 3.3V, you can follow these steps based on the provided search results:

    Connecting the BMP280 Sensor:
        Connect the BMP280 sensor to the Raspberry Pi using I2C communication protocol.
        Wire the sensor as follows:
            VCC pin to PIN 17 on the Raspberry Pi board.
            GND pin to PIN 9 of the Raspberry Pi board.
            SCL pin to GPIO3 (PIN 5) on the Raspberry Pi board.
            SDA pin to GPIO2 (PIN 3) on the Raspberry Pi board.
            
    Installing Libraries:
        To enable communication with the BMP280 sensor, install necessary libraries using Pypi, a Python package index repository.
        Open the terminal on your Raspberry Pi and run the following commands:

        sudo pip install bmp280
        git clone https://github.com/pimoroni/bmp280-python
        cd bmp280-python
        sudo ./install.sh
        cd examples

    Use these commands to install the required libraries for the BMP280 sensor1

Configuring the Sensor:

    The BMP280 sensor is capable of measuring temperature, pressure, and altitude accurately.
    Ensure that you have connected the sensor correctly and installed the necessary libraries to start collecting data from the BMP280 sensor1.
```
