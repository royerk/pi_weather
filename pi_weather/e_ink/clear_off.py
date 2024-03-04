from pi_weather.e_ink.epd2in13_V4 import epd2in13_V4

epd = epd2in13_V4.EPD()

epd.init()
epd.Clear(0xFF)
epd.sleep()
