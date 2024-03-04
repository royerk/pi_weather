from pi_weather.e_ink.epd2in13_V4 import epd2in13_V4
from pi_weather.app.db_utils import DB_FILE
from PIL import Image,ImageDraw,ImageFont
import time
import sqlite3
import os

font24 = ImageFont.truetype(os.path.join('Font.ttc'), 24)

epd = epd2in13_V4.EPD()
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

data = {}
for row in rows:
    device_name = row[0]
    if device_name not in data:
        data[device_name] = {}
    data[device_name]["temperature"] = row[1]
    data[device_name]["humidity"] = row[2]
    data[device_name]["pressure"] = row[3]
    data[device_name]["date"] = row[4]

image = Image.new('1', (epd.height, epd.width), 255)
draw = ImageDraw.Draw(image)
x = 5
y = 5
y_delta = 30
for i, device_name in enumerate(data):
    text = f"{device_name}: {data[device_name]['temperature']:.1f} C, {data[device_name]['pressure']:.1f} hPa, {data[device_name]['date']}"
    draw.text((x, y + i * y_delta), text, font=font24, fill=0)
epd.display(epd.getbuffer(image))
epd.sleep()
