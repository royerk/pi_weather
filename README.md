# pi_weather

This is a simple weather station that uses a Raspberry Pi and a BMP280 sensor to measure temperature, ~~humidity~~, and pressure. The data is then sent to a web server.

To do:

- sensor retry
- e-ink display
- sample data, avoid artifacts

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

## Installation - E-ink

The `deploy-e-ink`/`update-e-ink`/`remove-e-ink` Makefile targets assume a
`.env`-configured `REMOTE_USER`/`REMOTE_HOST_E_INK`/`REMOTE_PATH` — that
setup isn't in use on the current e-ink hardware. Deploying there is
currently a manual SSH process instead:

- SSH directly into the Pi, e.g. `ssh kevin@hermes.local` (mDNS `.local`
  hostname — plain `hermes` won't resolve without it).
- Enable SPI if it isn't already: `sudo raspi-config nonint do_spi 0`.
  On Raspberry Pi OS / Debian trixie this took effect immediately
  (`/dev/spidev0.0`/`spidev0.1` appeared right away) — no reboot needed.
- Install system build dependencies (see
  [pi_weather/e_ink/README.md](pi_weather/e_ink/README.md) for why each
  one is needed): `sudo apt-get install -y python3-dev swig liblgpio-dev`.
- Copy the code over (e.g. `git ls-files -z | tar -czf code.tar.gz --null -T -`
  locally, `scp` it to the Pi, extract), then set up the venv:
  ```bash
  python3 -m venv venv-ink
  source venv-ink/bin/activate
  pip install -r requirements-ink.txt
  ```
- Run once to verify it works: `venv-ink/bin/python3 -m pi_weather.e_ink.status`
- Add the cron job:
  ```bash
  (crontab -l 2>/dev/null; echo "2-59/5 * * * * cd ~/pi_weather && venv-ink/bin/python -m pi_weather.e_ink.status") | crontab -
  ```

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
