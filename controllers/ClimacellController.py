import json
from typing import List
from PIL import ImageFont, ImageDraw

from IT8951.display import AutoDisplay
from models.climacell.ClimacellResponse import climacell_response_decoder, ClimacellResponse
from models.AppConstants import AppConstants
from backports.zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from types import SimpleNamespace
import concurrent.futures


class ClimacellController:

    def __init__(self):
        self.future_forecasts: List[ClimacellResponse]
        self.font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 40)

    def fetch_weather(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fut = executor.submit(self.download_climacell_response)
            #  fut.add_done_callback(ClimacellController.on_future_complete)
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
        response = SimpleNamespace()
        # from 16:00UTC = 18:00 BP time
        response.text = '[{"lat":47.524862,"lon":19.082513,"temp":{"value":8.68,"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":75,"units":"%"},' \
                        '"weather_code":{"value":"rain_light"},"observation_time":{"value":"2020-12-12T16:00:00.000Z"}},' \
                        '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.67,"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":80,"units":"%"},' \
                        '"weather_code":{"value":"rain_light"},"observation_time":{"value":"2020-12-12T17:00:00.000Z"}},' \
                        '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.53,"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":60,"units":"%"},' \
                        '"weather_code":{"value":"drizzle"},"observation_time":{"value":"2020-12-12T18:00:00.000Z"}},' \
                        '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.44,"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":50,"units":"%"},' \
                        '"weather_code":{"value":"drizzle"},"observation_time":{"value":"2020-12-12T19:00:00.000Z"}},' \
                        '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.42,"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":50,"units":"%"},' \
                        '"weather_code":{"value":"drizzle"},"observation_time":{"value":"2020-12-12T20:00:00.000Z"}},' \
                        '{"lat":47.524862,"lon":19.082513,"temp":{"value":8.42,"units":"C"},' \
                        '"precipitation_type":{"value":"rain"},"precipitation_probability":{"value":50,"units":"%"},' \
                        '"weather_code":{"value":"drizzle"},"observation_time":{"value":"2020-12-12T21:00:00.000Z"}}]'
        decoded: List[ClimacellResponse] = json.loads(response.text, object_hook=climacell_response_decoder)
        self.future_forecasts = [future_forecast for future_forecast in decoded if
                            future_forecast.observation_time > datetime.now(ZoneInfo(AppConstants.local_time_zone))]
        print("decoded")

    def display_data_if_any(self, display: AutoDisplay):
        image_draw = ImageDraw.Draw(display.frame_buf)

        for num, forecast in enumerate(self.future_forecasts):
            # image_draw.rectangle((5, 5, 780, 145), fill=255)
            image_draw.text((10 + num * 150, 400),
                            text=self.format_date(forecast.observation_time), font=self.font)
            image_draw.text((10 + num * 150, 450),
                            text=str(forecast.temp) + "°C", font=self.font)
            image_draw.text((10 + num * 150, 500),
                            text=str(forecast.precipitation_probability) + "%", font=self.font)

    def format_date(self, date: datetime) -> str:
        return date.strftime("%H:%M")
