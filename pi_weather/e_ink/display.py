import os
import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from pi_weather.app.db_utils import get_alias, get_latest_sensor_data
from pi_weather.e_ink.epd2in13_V4 import EPD

font20 = ImageFont.truetype(os.path.join(os.path.dirname(__file__), "Font.ttc"), 20)

epd = EPD()
epd.init()
epd.Clear(0xFF)
time.sleep(2)

aliases = get_alias()

data = get_latest_sensor_data()
current_date = datetime.now()

if len(data) == 0:
    epd.sleep()
    exit()

image = Image.new("1", (epd.height, epd.width), 255)
draw = ImageDraw.Draw(image)
x = 5
y = 5
y_delta = 25


draw.text(
    (x, y),
    f"{current_date.strftime('%b %d, %H:%M')}",
    font=font20,
    fill=0,
)
y += y_delta

for i, device_name in enumerate(data):
    device_alias = aliases.get(device_name, device_name)
    delta_seconds = (current_date - data[device_name]["date"]).total_seconds()
    delta_minutes = int(delta_seconds / 60)
    text = f"{device_alias}: {data[device_name]['temperature']:.1f} C ({delta_minutes}m ago)"
    draw.text((x, y + i * y_delta), text, font=font20, fill=0)
epd.display(epd.getbuffer(image))
epd.sleep()
