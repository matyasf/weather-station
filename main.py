import argparse
from sys import path
from time import sleep
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import requests
from PIL import ImageFont, ImageDraw
from backports.zoneinfo import ZoneInfo
from models import AppConstants
from IT8951 import constants
import json
from typing import List
from models.climacell.ClimacellResponse import climacell_response_decoder, ClimacellResponse
from models.AppConstants import AppConstants

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


def init_display():
    # display is a 8 bit pixel B&W image
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
    return display


def refresh_time_text(display):
    image_draw = ImageDraw.Draw(display.frame_buf)
    image_draw.rectangle((5, 5, 780, 145), fill=255)
    now = datetime.now()
    image_draw.text((5, -50, 5, 5), text=now.strftime("%H:%M:%S"), font=time_font)
    display.draw_partial(constants.DisplayModes.GC16)


def fetch_weather():
    # +put here error handling
    time_end = (datetime.utcnow() + timedelta(hours=5)).replace(microsecond=0).isoformat()
    url = "https://api.climacell.co/v3/weather/forecast/hourly"# returns hourly results, time in GMT
    querystring = {"lat": AppConstants.forecast_lat, "lon": AppConstants.forecast_lon, "unit_system": "si", "start_time": "now",
                   "end_time": time_end, "fields": "precipitation_probability,temp,precipitation_type,weather_code",
                   "apikey": "u0q4InQgQv6dd5scyrcwy9oP0w10G1yo"}
    #response = requests.request("GET", url, params=querystring)
    response = SimpleNamespace()
    # from 16:00UTC = 18:00 BP time
    response.text = '[{"lat":47.524862,"lon":19.082513,"temp":{"value":8.68,"units":"C"},' \
                    '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":75,"units":"%"},' \
                    '"weather_code":{"value":"rain_light"},"observation_time":{"value":"2020-10-12T16:00:00.000Z"}},' \
                    '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.67,"units":"C"},' \
                    '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":80,"units":"%"},' \
                    '"weather_code":{"value":"rain_light"},"observation_time":{"value":"2020-10-12T17:00:00.000Z"}},' \
                    '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.53,"units":"C"},' \
                    '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":60,"units":"%"},' \
                    '"weather_code":{"value":"drizzle"},"observation_time":{"value":"2020-10-12T18:00:00.000Z"}},' \
                    '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.44,"units":"C"},' \
                    '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":50,"units":"%"},' \
                    '"weather_code":{"value":"drizzle"},"observation_time":{"value":"2020-10-12T19:00:00.000Z"}},' \
                    '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.42,"units":"C"},' \
                    '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":50,"units":"%"},' \
                    '"weather_code":{"value":"drizzle"},"observation_time":{"value":"2020-10-12T20:00:00.000Z"}},' \
                    '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.42,"units":"C"},' \
                    '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":50,"units":"%"},' \
                    '"weather_code":{"value":"drizzle"},"observation_time":{"value":"2020-10-12T21:00:00.000Z"}}]'
    decoded: List[ClimacellResponse] = json.loads(response.text, object_hook=climacell_response_decoder)
    future_forecasts = [future_forecast for future_forecast in decoded if future_forecast.observation_time > datetime.now(ZoneInfo(AppConstants.local_time_zone))]
    print("decoded")
    # + code to display it


if __name__ == '__main__':
    args = parse_args()
    display = init_display()
    display.draw_full(constants.DisplayModes.GC16)
    time_font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 185)
    last_weather_refresh_time = datetime.fromisoformat("2000-01-01")
    while True:
        start_time = datetime.now()
        refresh_time_text(display)
        if (last_weather_refresh_time + timedelta(minutes=60)) < start_time:
            last_weather_refresh_time = start_time
            fetch_weather()
            print("refresh weather")
        # + code to get data from BME680
        elapsed_time = datetime.now() - start_time
        if elapsed_time.total_seconds() < 1:
            sleep_duration = 1 - elapsed_time.total_seconds() - 0.01
            print("sleep " + str(sleep_duration) + " secs")
            sleep(sleep_duration)
