# 2.13 in e-ink

- [epd_2in13_V4_test](https://github.com/waveshareteam/e-Paper/blob/master/RaspberryPi_JetsonNano/python/examples/epd_2in13_V4_test.py)
- font taken from pic dir
- epd_2in13_V4 from repo as well
- [instructions](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual)

## Pi setup notes (found during real hardware deploy, Sep 2026)

On a Raspberry Pi OS / Debian trixie (aarch64) host that had SPI disabled
(e.g. a Pi that previously ran this project but had SPI turned back off):

1. **Enable SPI**: `sudo raspi-config nonint do_spi 0`. On this OS/firmware
   version this took effect immediately (`/dev/spidev0.0`/`spidev0.1`
   appeared right away) — no reboot needed. It also uncomments
   `dtparam=spi=on` in `/boot/firmware/config.txt` so it survives a reboot.
1. **System build dependencies**, needed before `pip install -r requirements-ink.txt` will succeed — `RPi.GPIO`, `spidev`, and `lgpio`
   are all C extensions built from source on install:
   ```bash
   sudo apt-get install -y python3-dev swig liblgpio-dev
   ```
   Without `python3-dev`, both `RPi.GPIO` and `spidev` fail with
   `fatal error: Python.h: No such file or directory`. Without `swig`,
   `lgpio` fails at `swig -python -o lgpio_wrap.c lgpio.i`. Without
   `liblgpio-dev`, `lgpio` builds but fails to link
   (`cannot find -llgpio`).
1. **`lgpio` is required, not optional**, despite not being in the original
   `requirements-ink.txt` — without it, `gpiozero` (used by `epdconfig.py`
   for the BUSY pin) falls back to legacy `RPi.GPIO` edge detection, which
   fails on this kernel with `RuntimeError: Failed to add edge detection`.
   Installing `lgpio` lets `gpiozero` use the modern gpiochip-based pin
   factory instead, which works. Already added to `requirements-ink.txt`.
