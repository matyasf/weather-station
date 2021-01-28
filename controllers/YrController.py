import json
import random
import traceback
import requests
import concurrent.futures

from asyncio import Future
from typing import List
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo # TODO test for Pyton 3.9
except ImportError: # for Python < 3.9
    from backports.zoneinfo import ZoneInfo
from PIL import ImageFont, ImageDraw, Image
from IT8951.display import AutoDisplay
from controllers.SunriseSunsetCalculator import SunriseSunsetCalculator
from models.yr import yr_yr_mapping
from models.AppConstants import AppConstants
from models.yr.YrResponse import yr_response_decoder, YrResponse
from Utils import Utils


class YrController:
    """
    class to download and display data from yr.no
    This API wants sends a time how long the results are valid, its approx. 30-40 mins.
    """
    def __init__(self):
        self.future_forecasts: List[YrResponse] = None
        self.font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 40)
        self.error_msg = ""

    def fetch_weather(self) -> None:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fut = executor.submit(self.download_yr_no_data)
            fut.add_done_callback(self.on_future_complete)
    
    def download_yr_no_data(self) -> None:
        url = "https://api.met.no/weatherapi/locationforecast/2.0/compact"  # returns hourly results
        querystring = {"lat": str(AppConstants.forecast_lat), "lon": str(AppConstants.forecast_lon),
                       "altitude": "90"}
        headers = {"user-agent": "weather-station/1.0 https://github.com/matyasf/weather-station",
                   "Accept": "application/json", "accept-encoding": "gzip, deflate"}
        response = requests.request("GET", url, params=querystring, headers=headers)
        decoded: dict = json.loads(response.text, object_hook=yr_response_decoder)
        forecast_list: List[YrResponse] = decoded['properties']['timeseries']
        forecast_list = forecast_list[:6]
        self.future_forecasts = [future_forecast for future_forecast in forecast_list if
                            future_forecast.observation_time > datetime.now(ZoneInfo(AppConstants.local_time_zone))]
        self.error_msg = ""
        Utils.log("Decoded yr.no response. length:" + str(len(forecast_list)) + " in future: " + str(len(self.future_forecasts)))


    def display_data_if_any(self, display: AutoDisplay) -> None:
        icon_y = 350
        text_y_start = 452
        column_width = 165
        if self.error_msg:
            image_draw = ImageDraw.Draw(display.frame_buf)
            display.frame_buf.paste(0xFF, box=(5, icon_y, 780, icon_y + 245))
            image_draw.multiline_text((5, icon_y), text=self.error_msg, font=self.font)
            return
        if self.future_forecasts is None: # No new forecast to display
            return

        Utils.log("displaying yr.no data")
        image_draw = ImageDraw.Draw(display.frame_buf)
        display.frame_buf.paste(0xFF, box=(5, icon_y, 780, icon_y + 245))

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
            # display weather forecast TODO
            weather_icon: str = yr_yr_mapping.yr_yr_map.get(forecast.weather_code)
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
            if forecast.precipitation_amount > 0:
                rain_icon = Image.open("assets/umbrella-rain-icon.png")
                display.frame_buf.paste(rain_icon, (5 + num * column_width, text_y_start + 106))
                image_draw.text((10 + num * column_width + 26, text_y_start + 98),
                                text=str(forecast.precipitation_amount) + "mm", font=self.font)
            num = num + 1
        self.future_forecasts = None

    def on_future_complete(self, future: Future) -> None:
        if future.exception():
            self.error_msg = ":( Yr: " + repr(future.exception())
            self.error_msg = '\n'.join(self.error_msg[i:i + 40] for i in range(0, len(self.error_msg), 40))
            Utils.log("YrController raised error:\n" + "".join(traceback.TracebackException.from_exception(future.exception()).format()))
