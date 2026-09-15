import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from pi_weather.e_ink.epd2in13_V4 import EPD
from pi_weather.e_ink.status_data import (
    read_cpu_temp,
    read_docker_status,
    read_uptime,
    record_full_refresh,
    should_do_full_refresh,
)

STATE_FILE = "/tmp/pi_weather_eink_last_full_refresh"
DOCKER_LINE_MAX_CHARS = 30

font20 = ImageFont.truetype(os.path.join(os.path.dirname(__file__), "Font.ttc"), 20)

now = datetime.now()
full_refresh = should_do_full_refresh(STATE_FILE, now)

epd = EPD()
epd.init()
if full_refresh:
    epd.Clear(0xFF)

image = Image.new("1", (epd.height, epd.width), 255)
draw = ImageDraw.Draw(image)
x = 5
y = 5
y_delta = 25

draw.text((x, y), now.strftime("%b %d, %H:%M"), font=font20, fill=0)
y += y_delta

cpu_temp = read_cpu_temp()
cpu_line = f"CPU: {cpu_temp:.1f} C" if cpu_temp is not None else "CPU: n/a"
draw.text((x, y), cpu_line, font=font20, fill=0)
y += y_delta

uptime = read_uptime()
uptime_line = f"Up: {uptime}" if uptime is not None else "Up: n/a"
draw.text((x, y), uptime_line, font=font20, fill=0)
y += y_delta

containers = read_docker_status()
if containers is None:
    docker_lines = ["docker: n/a"]
elif len(containers) == 0:
    docker_lines = ["docker: none running"]
else:
    docker_lines = [line[:DOCKER_LINE_MAX_CHARS] for line in containers]

for i, line in enumerate(docker_lines):
    draw.text((x, y + i * y_delta), line, font=font20, fill=0)

image = image.rotate(180)

if full_refresh:
    epd.displayPartBaseImage(epd.getbuffer(image))
    record_full_refresh(STATE_FILE, now)
else:
    epd.displayPartial(epd.getbuffer(image))

epd.sleep()
