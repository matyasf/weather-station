import json
import random
from asyncio import Future
from typing import List
from PIL import ImageFont, ImageDraw, Image

from IT8951.display import AutoDisplay
from models.climacell import climacell_yr_mapping
from models.climacell.ClimacellResponse import climacell_response_decoder, ClimacellResponse
from models.AppConstants import AppConstants
from backports.zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from types import SimpleNamespace
import concurrent.futures


class ClimacellController:

    def __init__(self):
        self.future_forecasts: List[ClimacellResponse] = None
        self.font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 40)

    def fetch_weather(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fut = executor.submit(self.download_climacell_response)
            fut.add_done_callback(self.on_future_complete)
        # + code to display it

    def download_climacell_response(self):
        # +put here error handling
        time_end = (datetime.utcnow() + timedelta(hours=5)).replace(microsecond=0).isoformat()
        url = "https://api.climacell.co/v3/weather/forecast/hourly"  # returns hourly results, time in GMT
        querystring = {"lat": AppConstants.forecast_lat, "lon": AppConstants.forecast_lon, "unit_system": "si",
                       "start_time": "now",
                       "end_time": time_end, "fields": "precipitation_probability,temp,precipitation_type,weather_code",
                       "apikey": "u0q4InQgQv6dd5scyrcwy9oP0w10G1yo"}
        # response = requests.request("GET", url, params=querystring)
        response = self.test_response()
        decoded: List[ClimacellResponse] = json.loads(response.text, object_hook=climacell_response_decoder)
        self.future_forecasts = [future_forecast for future_forecast in decoded if
                            future_forecast.observation_time > datetime.now(ZoneInfo(AppConstants.local_time_zone))]
        print("decoded")

    def display_data_if_any(self, display: AutoDisplay):
        if self.future_forecasts == None:
            return
        image_draw = ImageDraw.Draw(display.frame_buf)
        text_y_start = 450
        column_width = 165
        icon_y = 350
        image_draw.rectangle((5, icon_y, 780, icon_y + 245), fill=255)
        for num, forecast in enumerate(self.future_forecasts):
            # draw icon
            weather_icon = climacell_yr_mapping.climacell_yr_map.get(forecast.weather_code)
            # these have day/night variations
            if weather_icon == "03" or weather_icon == "02" or weather_icon == "01":
                if forecast.observation_time.hour > 7 and forecast.observation_time.hour < 20:
                    weather_icon = weather_icon + "d"
                else:
                    weather_icon = weather_icon + "n"
            icon_bmp = Image.open("assets/yr_icons_100/" + weather_icon + ".png")
            image_draw.bitmap((10 + num * column_width, icon_y), icon_bmp)

            image_draw.text((10 + num * column_width, text_y_start),
                            text=forecast.observation_time.strftime("%H:%M"), font=self.font)
            image_draw.text((10 + num * column_width, text_y_start + 50),
                            text=str(forecast.temp) + "°C", font=self.font)
            image_draw.text((10 + num * column_width, text_y_start + 100),
                            text=str(forecast.precipitation_probability) + "%", font=self.font)
        self.future_forecasts = None

    def on_future_complete(self, future: Future):
        if future.exception():
            print("ClimacellController raised error: " + str(future.exception()))

    def test_response(self):
        response = SimpleNamespace()
        # from 16:00UTC = 18:00 BP time
        response.text = '[{"lat":47.524862,"lon":19.082513,"temp":{"value":' + str(random.randrange(-30, 44)) + ',"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":' + str(random.randrange(0, 99)) + ',"units":"%"},' \
                        '"weather_code":{"value":"' + random.choice(list(climacell_yr_mapping.climacell_yr_map)) + '"},"observation_time":{"value":"2020-12-12T16:00:00.000Z"}},' \
                        '{"lat":47.524862,"lon":19.082513,"temp":{"value":' + str(random.randrange(-30, 44)) + ',"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":' + str(random.randrange(0, 99)) + ',"units":"%"},' \
                        '"weather_code":{"value":"' + random.choice(list(climacell_yr_mapping.climacell_yr_map)) + '"},"observation_time":{"value":"2020-12-12T17:00:00.000Z"}},' \
                        '{"lat":47.524862,"lon":19.082513,"temp":{"value":' + str(random.randrange(-30, 44))+ ',"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":' + str(random.randrange(0, 99)) + ',"units":"%"},' \
                        '"weather_code":{"value":"' + random.choice(list(climacell_yr_mapping.climacell_yr_map)) + '"},"observation_time":{"value":"2020-12-12T18:00:00.000Z"}},' \
                        '{"lat":47.524862,"lon":19.082513,"temp":{"value":' + str(random.randrange(-30, 44)) + ',"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":' + str(random.randrange(0, 99)) + ',"units":"%"},' \
                        '"weather_code":{"value":"' + random.choice(list(climacell_yr_mapping.climacell_yr_map)) + '"},"observation_time":{"value":"2020-12-12T19:00:00.000Z"}},' \
                        '{"lat":47.524862,"lon":19.082513,"temp":{"value":' + str(random.randrange(-30, 44)) + ',"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":' + str(random.randrange(0, 99)) + ',"units":"%"},' \
                        '"weather_code":{"value":"' + random.choice(list(climacell_yr_mapping.climacell_yr_map)) + '"},"observation_time":{"value":"2020-12-12T20:00:00.000Z"}}]'
        return response
