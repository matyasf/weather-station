import json
import random
import traceback
from asyncio import Future
from typing import List

import requests
from PIL import ImageFont, ImageDraw, Image

from IT8951.display import AutoDisplay

from Utils import Utils
from controllers.SunriseSunsetCalculator import SunriseSunsetCalculator
from models.climacell import climacell_yr_mapping
from models.climacell.ClimacellResponse import climacell_response_decoder, ClimacellResponse
from models.AppConstants import AppConstants
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from types import SimpleNamespace
import concurrent.futures


class ClimacellController:
    """
    class to download and display data from tomorrow.io
    This API allows 100 requests/day, so one approx. every 15 mins.
    """
    def __init__(self):
        self.future_forecasts: List[ClimacellResponse] = None
        self.font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 40)
        self.error_msg = ""

    def fetch_weather(self) -> None:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fut = executor.submit(self.download_climacell_data)
            fut.add_done_callback(self.on_future_complete)

    def download_climacell_data(self) -> None:
        time_end = (datetime.utcnow() + timedelta(hours=7)).replace(microsecond=0, tzinfo=ZoneInfo(AppConstants.local_time_zone)).isoformat()
        time_start = (datetime.utcnow().replace(microsecond=0, second=0, minute=0, tzinfo=ZoneInfo(AppConstants.local_time_zone))
                      + timedelta(hours=1)).isoformat()
        url = "https://api.tomorrow.io/v4/timelines"  # returns hourly results, time in GMT
        querystring = {"location": str(AppConstants.forecast_lat) + "," + str(AppConstants.forecast_lon),
                    "timesteps":"1h", "apikey": "29D9C1vDbosbtwptFjl1p12gYGVDe462", "endTime": time_end,"startTime": time_start,
                    "fields": "precipitationProbability,temperature,precipitationType,weatherCode"}
        response = requests.request("GET", url, params=querystring)
        #response = self.test_response_no_precip() # use this for testing to not use up the API
        decoded: dict = json.loads(response.text, object_hook=climacell_response_decoder)
        forecast_list: List[ClimacellResponse] = decoded['data']['timelines'][0]['intervals']
        self.future_forecasts = [future_forecast for future_forecast in forecast_list if
                            future_forecast.observation_time > datetime.now(ZoneInfo(AppConstants.local_time_zone))]
        self.error_msg = ""
        #Utils.log("Decoded tomorrow.io response. length:" + str(len(forecast_list)) + " in future: " + str(len(self.future_forecasts)))

    def display_data_if_any(self, display: AutoDisplay) -> None:
        icon_y = 365
        text_y_start = 445
        column_width = 165
        if self.error_msg:
            image_draw = ImageDraw.Draw(display.frame_buf)
            display.frame_buf.paste(0xFF, box=(5, icon_y, 790, icon_y + 245))
            image_draw.multiline_text((5, icon_y), text=self.error_msg, font=self.font)
            return
        if self.future_forecasts is None: # No new forecast to display
            return
        
        has_precipitation_prob = False
        for forecast in self.future_forecasts:
            if forecast.precipitation_probability > 0:
                has_precipitation_prob = True
        if has_precipitation_prob == False:
            text_y_start = text_y_start + 25
            icon_y = icon_y + 20

        # Utils.log("displaying climacell data")
        image_draw = ImageDraw.Draw(display.frame_buf)
        display.frame_buf.paste(0xFF, box=(5, icon_y, 790, icon_y + 245))

        now_time = datetime.now(ZoneInfo(AppConstants.local_time_zone))
        timezone_offset = int(now_time.utcoffset() / timedelta(hours=1))
        sunrise = SunriseSunsetCalculator.calculate_sunrise(
            AppConstants.forecast_lat, AppConstants.forecast_lon, timezone_offset).astimezone(ZoneInfo(AppConstants.local_time_zone))
        sunrise_displayed = False
        sunset = SunriseSunsetCalculator.calculate_sunset(
            AppConstants.forecast_lat, AppConstants.forecast_lon, timezone_offset).astimezone(ZoneInfo(AppConstants.local_time_zone))
        sunset_displayed = False
        num = 0
        for forecast in self.future_forecasts:
            # display sunrise/sunset icon and time.
            # Note: The sunrise will not be displayed if its before 4am and the time is before midnight because sunrise
            # is calculated for the current day only. Its also buggy if the sun does not set/rise.
            if now_time < sunrise < forecast.observation_time and sunrise_displayed == False:
                icon_bmp = Image.open("assets/yr_icons_100/sunrise.png")
                display.frame_buf.paste(icon_bmp, (10 + num * column_width, icon_y))
                image_draw.text((10 + num * column_width, text_y_start),
                                text=sunrise.strftime("%H:%M"), font=self.font)
                sunrise_displayed = True
                num = num + 1
            if now_time < sunset < forecast.observation_time and sunset_displayed == False:
                icon_bmp = Image.open("assets/yr_icons_100/sunset.png")
                display.frame_buf.paste(icon_bmp, (10 + num * column_width, icon_y))
                image_draw.text((10 + num * column_width, text_y_start),
                                text=sunset.strftime("%H:%M"), font=self.font)
                sunset_displayed = True
                num = num + 1
            # display weather forecast
            weather_icon: str = climacell_yr_mapping.climacell_yr_map.get(forecast.weather_code)
            # these have day/night variations
            if weather_icon == "03" or weather_icon == "02" or weather_icon == "01":
                if sunrise < forecast.observation_time < sunset:
                    weather_icon = weather_icon + "d"
                else:
                    weather_icon = weather_icon + "n"
            icon_bmp = Image.open("assets/yr_icons_100/" + weather_icon + ".png")
            display.frame_buf.paste(icon_bmp, (10 + num * column_width, icon_y))

            image_draw.text((10 + num * column_width, text_y_start),
                            text=forecast.observation_time.strftime("%H:%M"), font=self.font)
            image_draw.text((10 + num * column_width, text_y_start + 50),
                            text=str(forecast.temp) + "°C", font=self.font)
            if forecast.precipitation_probability > 0:
                rain_icon = Image.open("assets/umbrella-rain-icon.png")
                display.frame_buf.paste(rain_icon, (5 + num * column_width, text_y_start + 106))
                image_draw.text((10 + num * column_width + 26, text_y_start + 98),
                                text=str(forecast.precipitation_probability) + "%", font=self.font)
            num = num + 1
        self.future_forecasts = None

    def on_future_complete(self, future: Future) -> None:
        if future.exception():
            self.error_msg = ":( Climacell: " + repr(future.exception())
            self.error_msg = '\n'.join(self.error_msg[i:i + 40] for i in range(0, len(self.error_msg), 40))
            Utils.log("ClimacellController raised error:\n" + "".join(traceback.TracebackException.from_exception(future.exception()).format()))

    @staticmethod
    def test_response() -> SimpleNamespace:
        response = SimpleNamespace()
        response.text ="""{"data":{
        "timelines":
            [{"timestep":"1h","startTime":"2021-01-05T20:06:48Z","endTime":"2021-01-05T23:06:48Z","intervals":
                [{"startTime":"2031-01-05T20:06:48Z",
                "values":{"precipitationProbability":9,"temperature":3.23,"precipitationType":1,"weatherCode":1101}},
                {"startTime":"2031-01-05T21:06:48Z",
                "values":{"precipitationProbability":0.6,"temperature":3.12,"precipitationType":2,"weatherCode":1001}},
                {"startTime":"2031-01-05T22:06:48Z",
                "values":{"precipitationProbability":5,"temperature":3.09,"precipitationType":2,"weatherCode":1001}},
                {"startTime":"2031-01-05T23:06:48Z",
                "values":{"precipitationProbability":5,"temperature":3.2,"precipitationType":2,"weatherCode":1001}},
                {"startTime":"2031-01-06T00:06:48Z",
                "values":{"precipitationProbability":95,"temperature":33.2,"precipitationType":2,"weatherCode":1001}}
            ]}
        ]}}"""
        return response
    
    @staticmethod
    def test_response_no_precip() -> SimpleNamespace:
        response = SimpleNamespace()
        response.text ="""{"data":{
        "timelines":
            [{"timestep":"1h","startTime":"2021-01-05T20:06:48Z","endTime":"2021-01-05T23:06:48Z","intervals":
                [{"startTime":"2031-01-05T20:06:48Z",
                "values":{"precipitationProbability":0,"temperature":3.23,"precipitationType":1,"weatherCode":1101}},
                {"startTime":"2031-01-05T21:06:48Z",
                "values":{"precipitationProbability":0,"temperature":3.12,"precipitationType":2,"weatherCode":1001}},
                {"startTime":"2031-01-05T22:06:48Z",
                "values":{"precipitationProbability":0,"temperature":3.09,"precipitationType":2,"weatherCode":1001}},
                {"startTime":"2031-01-05T23:06:48Z",
                "values":{"precipitationProbability":0,"temperature":3.2,"precipitationType":2,"weatherCode":1001}},
                {"startTime":"2031-01-06T00:06:48Z",
                "values":{"precipitationProbability":0,"temperature":33.2,"precipitationType":2,"weatherCode":1001}}
            ]}
        ]}}"""
        return response
