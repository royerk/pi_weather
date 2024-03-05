import os
import sqlite3
import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from pi_weather.app.db_utils import DB_FILE, get_alias
from pi_weather.e_ink.epd2in13_V4 import EPD

font20 = ImageFont.truetype(os.path.join(os.path.dirname(__file__), "Font.ttc"), 20)

epd = EPD()
epd.init()
epd.Clear(0xFF)
time.sleep(2)

with sqlite3.connect(DB_FILE) as conn:
    cursor = conn.cursor()
    query = """
                SELECT s1.device_name,
                    s1.temperature,
                    s1.humidity,
                    s1.pressure,
                    s1.date
                FROM sensor_data s1
                JOIN (
                    SELECT device_name, MAX(date) AS max_date
                    FROM sensor_data
                    GROUP BY device_name
                ) s2
                ON s1.device_name = s2.device_name AND s1.date = s2.max_date;
            """
    cursor.execute(query)
    rows = cursor.fetchall()

if len(rows) == 0:
    epd.sleep()
    exit()

aliases = get_alias()

data = {}
max_date = None
for row in rows:
    device_name = row[0]
    if device_name not in data:
        data[device_name] = {}
    data[device_name]["temperature"] = row[1]
    data[device_name]["humidity"] = row[2]
    data[device_name]["pressure"] = row[3]
    data[device_name]["date"] = datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S")
    max_date = (
        max(max_date, data[device_name]["date"])
        if max_date
        else data[device_name]["date"]
    )

image = Image.new("1", (epd.height, epd.width), 255)
draw = ImageDraw.Draw(image)
x = 5
y = 5
y_delta = 25

delta_seconds = (datetime.now() - max_date).total_seconds()
delta_minutes = int(delta_seconds / 60)
draw.text(
    (x, y),
    f"{max_date.strftime('%b %d, %H:%M')}, {delta_minutes}m ago",
    font=font20,
    fill=0,
)
y += y_delta

for i, device_name in enumerate(data):
    device_name = aliases.get(device_name, device_name)
    text = f"{device_name}: {data[device_name]['temperature']:.1f} C"
    if data[device_name]["date"] != max_date:
        text = f"{device_name}: Ø"
    draw.text((x, y + i * y_delta), text, font=font20, fill=0)
epd.display(epd.getbuffer(image))
epd.sleep()
