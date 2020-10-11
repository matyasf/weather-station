import argparse
from sys import path
from time import sleep
from datetime import datetime, timedelta
from PIL import ImageFont, ImageDraw, Image
from IT8951 import constants
import requests
import json

from models.climacell.ClimacellResponse import climacell_response_decoder

path += ['../IT8951/IT8951']


def parse_args():
    p = argparse.ArgumentParser(description='Test EPD functionality')
    p.add_argument('-v', '--virtual', action='store_true',
                   help='display using a Tkinter window instead of the '
                        'actual e-paper device (for testing without a '
                        'physical device)')
    p.add_argument('-r', '--rotate', default=None, choices=['CW', 'CCW', 'flip'],
                   help='run the tests with the display rotated by the specified value')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if not args.virtual:
        from IT8951.display import AutoEPDDisplay
        print('Initializing EPD...')
        # here, spi_hz controls the rate of data transfer to the device, so a higher
        # value means faster display refreshes. the documentation for the IT8951 device
        # says the max is 24 MHz (24000000), but my device seems to still work as high as
        # 80 MHz (80000000)
        display = AutoEPDDisplay(vcom=-2.06, rotate=args.rotate, spi_hz=24000000)
        print('VCOM set to', display.epd.get_vcom())
    else:
        from IT8951.display import VirtualEPDDisplay
        display = VirtualEPDDisplay(dims=(800, 600), rotate=args.rotate)
        print("initializing virtual display")

    # TEST
    time_end = (datetime.utcnow() + timedelta(days=2)).replace(microsecond=0).isoformat()
    url = "https://api.climacell.co/v3/weather/forecast/hourly"
    # BP coordinates
    querystring = {"lat": "47.524862", "lon": "19.082513", "unit_system": "si", "start_time": "now",
                   "end_time": time_end, "fields": "precipitation_probability,temp,precipitation_type,weather_code",
                   "apikey": "u0q4InQgQv6dd5scyrcwy9oP0w10G1yo"}
    #response = requests.request("GET", url, params=querystring)
    #response.text
    response = """
    [{"lat":47.524862,"lon":19.082513,
     "temp":{"value":7.27,"units":"C"},
     "precipitation_type":{"value":"rain"},
     "precipitation_probability":{"value":65,"units":"%"},
     "weather_code":{"value":"drizzle"},
     "observation_time":{"value":"2020-10-13T17:00:00.000Z"}}]
    """
    decoded = json.loads(response, object_hook=climacell_response_decoder)

    # draw some text
    fnt = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 185)
    image_draw = ImageDraw.Draw(display.frame_buf)
    image_draw.text((10, -50), text="23:45:38", font=fnt)

    # update display
    display.draw_full(constants.DisplayModes.GC16)

    sleep(2)
