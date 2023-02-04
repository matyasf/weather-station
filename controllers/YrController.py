import json
import random
import traceback
import requests
import concurrent.futures

from types import SimpleNamespace
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
                       "altitude": str(AppConstants.height_above_sea)}
        headers = {"user-agent": "weather-station/1.0 https://github.com/matyasf/weather-station",
                   "Accept": "application/json", "accept-encoding": "gzip, deflate"}
        response = requests.request("GET", url, params=querystring, headers=headers)
        #response = self.test_response()
        decoded: dict = json.loads(response.text, object_hook=yr_response_decoder)
        forecast_list: List[YrResponse] = decoded['properties']['timeseries']
        forecast_list = forecast_list[:6]
        self.future_forecasts = [future_forecast for future_forecast in forecast_list if
                            future_forecast.observation_time > datetime.now(ZoneInfo(AppConstants.local_time_zone))]
        self.error_msg = ""
        #Utils.log("Decoded yr.no response. length:" + str(len(forecast_list)) + " in future: " + str(len(self.future_forecasts)))


    def display_data_if_any(self, display: AutoDisplay) -> None:
        icon_y = 350
        text_y_start = 452
        column_width = 155
        left_margin = 36
        if self.error_msg:
            image_draw = ImageDraw.Draw(display.frame_buf)
            display.frame_buf.paste(0xFF, box=(5, icon_y, 790, icon_y + 245))
            image_draw.multiline_text((5, icon_y), text=self.error_msg, font=self.font)
            return
        if self.future_forecasts is None: # No new forecast to display
            return

        Utils.log("displaying yr.no data")
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

        self.display_umbrella_icon_if_there_will_be_rain(display, text_y_start)
        
        num = 0
        for forecast in self.future_forecasts:
            # display sunrise/sunset icon and time.
            # Note: The sunrise will not be displayed if its before 4am and the time is before midnight because sunrise
            # is calculated for the current day only. Its also buggy if the sun does not set/rise.
            if now_time < sunrise < forecast.observation_time and sunrise_displayed == False:
                icon_bmp = Image.open("assets/yr_icons_100/sunrise.png")
                display.frame_buf.paste(icon_bmp, (left_margin + num * column_width, icon_y))
                image_draw.text((left_margin + num * column_width, text_y_start),
                                text=sunrise.strftime("%H:%M"), font=self.font)
                sunrise_displayed = True
                num = num + 1
            if now_time < sunset < forecast.observation_time and sunset_displayed == False:
                icon_bmp = Image.open("assets/yr_icons_100/sunset.png")
                display.frame_buf.paste(icon_bmp, (left_margin + num * column_width, icon_y))
                image_draw.text((left_margin + num * column_width, text_y_start),
                                text=sunset.strftime("%H:%M"), font=self.font)
                sunset_displayed = True
                num = num + 1
            # display weather forecast
            weather_icon: str = yr_yr_mapping.yr_yr_map.get(forecast.weather_code)
            # these have day/night variations
            icons_with_variants = ["01", "02", "03", "05", "06", "07", "08", "20", "21", "24", "25",
                                   "26", "27", "28", "29", "40", "41", "42", "43", "44", "45"]
            if weather_icon in icons_with_variants:
                if sunrise < forecast.observation_time < sunset:
                    weather_icon = weather_icon + "d"
                else:
                    weather_icon = weather_icon + "n"
            icon_bmp = Image.open("assets/yr_icons_100/" + weather_icon + ".png")
            display.frame_buf.paste(icon_bmp, (left_margin + num * column_width, icon_y))

            image_draw.text((left_margin + num * column_width, text_y_start),
                            text=forecast.observation_time.strftime("%H:%M"), font=self.font)
            image_draw.text((left_margin + num * column_width, text_y_start + 50),
                            text=str(forecast.temp) + "°C", font=self.font)
            if forecast.precipitation_amount > 0:
                image_draw.text((left_margin + num * column_width, text_y_start + 98),
                                text=str(forecast.precipitation_amount) + "mm", font=self.font)
            num = num + 1
        self.future_forecasts = None

    def on_future_complete(self, future: Future) -> None:
        if future.exception():
            self.error_msg = ":( Yr: " + repr(future.exception())
            self.error_msg = '\n'.join(self.error_msg[i:i + 40] for i in range(0, len(self.error_msg), 40))
            Utils.log("YrController raised error:\n" + "".join(traceback.TracebackException.from_exception(future.exception()).format()))
    
    def display_umbrella_icon_if_there_will_be_rain(self, display, text_y_start):
        will_there_be_rain = False
        for forecast in self.future_forecasts:
            if forecast.precipitation_amount > 0:
                will_there_be_rain = True
                break
        if will_there_be_rain:
            rain_icon = Image.open("assets/umbrella-rain-icon.png")
            display.frame_buf.paste(rain_icon, (5, text_y_start + 106))

    @staticmethod
    def test_response() -> SimpleNamespace:
        response = SimpleNamespace()
        response.text ="""
        {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
            19.0825,
            47.5249,
            90
            ]
        },
        "properties": {
            "meta": {
            "updated_at": "2021-01-28T20:50:41Z",
            "units": {
                "air_pressure_at_sea_level": "hPa",
                "air_temperature": "celsius",
                "cloud_area_fraction": "%",
                "precipitation_amount": "mm",
                "relative_humidity": "%",
                "wind_from_direction": "degrees",
                "wind_speed": "m/s"
            }
            },
            "timeseries": [
            {
                "time": "2021-01-28T23:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.9,
                    "air_temperature": 0.3,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 99.1,
                    "wind_from_direction": 198.3,
                    "wind_speed": 2.2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "sleet"
                    },
                    "details": {
                    "precipitation_amount": 0.3
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "lightsleet"
                    },
                    "details": {
                    "precipitation_amount": 0.7
                    }
                }
                }
            },
            {
                "time": "2021-01-29T00:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.4,
                    "air_temperature": 0.4,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 98,
                    "wind_from_direction": 223.3,
                    "wind_speed": 1.7
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "lightsleet"
                    },
                    "details": {
                    "precipitation_amount": 0.2
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.4
                    }
                }
                }
            },
            {
                "time": "2021-01-29T01:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.2,
                    "air_temperature": 0.3,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 97,
                    "wind_from_direction": 255.7,
                    "wind_speed": 1.2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.2
                    }
                }
                }
            },
            {
                "time": "2021-01-29T02:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.2,
                    "air_temperature": 0.7,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 94.3,
                    "wind_from_direction": 281.2,
                    "wind_speed": 1.7
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.2
                    }
                }
                }
            },
            {
                "time": "2021-01-29T03:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.3,
                    "air_temperature": 1.1,
                    "cloud_area_fraction": 99.2,
                    "relative_humidity": 92.7,
                    "wind_from_direction": 284,
                    "wind_speed": 2.3
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                }
                }
            },
            {
                "time": "2021-01-29T04:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.6,
                    "air_temperature": 1.2,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 93.5,
                    "wind_from_direction": 278.6,
                    "wind_speed": 3.1
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.4
                    }
                }
                }
            },
            {
                "time": "2021-01-29T05:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.9,
                    "air_temperature": 1,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 95,
                    "wind_from_direction": 271.2,
                    "wind_speed": 3
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    },
                    "details": {
                    "precipitation_amount": 0.6
                    }
                }
                }
            },
            {
                "time": "2021-01-29T06:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1003.1,
                    "air_temperature": 0.7,
                    "cloud_area_fraction": 82.8,
                    "relative_humidity": 95.5,
                    "wind_from_direction": 267.5,
                    "wind_speed": 2.5
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    },
                    "details": {
                    "precipitation_amount": 0.6
                    }
                }
                }
            },
            {
                "time": "2021-01-29T07:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1003.9,
                    "air_temperature": 1.1,
                    "cloud_area_fraction": 98.4,
                    "relative_humidity": 95.9,
                    "wind_from_direction": 257.4,
                    "wind_speed": 3.5
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 1
                    }
                }
                }
            },
            {
                "time": "2021-01-29T08:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1004.1,
                    "air_temperature": 1.9,
                    "cloud_area_fraction": 99.2,
                    "relative_humidity": 94.1,
                    "wind_from_direction": 262.1,
                    "wind_speed": 4
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 2.2
                    }
                }
                }
            },
            {
                "time": "2021-01-29T09:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1003.7,
                    "air_temperature": 2.3,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 93.2,
                    "wind_from_direction": 265.4,
                    "wind_speed": 3.2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 0.3
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 3.4
                    }
                }
                }
            },
            {
                "time": "2021-01-29T10:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.9,
                    "air_temperature": 2.3,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 93.3,
                    "wind_from_direction": 314.5,
                    "wind_speed": 1.4
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    },
                    "details": {
                    "precipitation_amount": 0.2
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 3.6
                    }
                }
                }
            },
            {
                "time": "2021-01-29T11:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.3,
                    "air_temperature": 2.2,
                    "cloud_area_fraction": 99.2,
                    "relative_humidity": 94.3,
                    "wind_from_direction": 225,
                    "wind_speed": 1.6
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 3.4
                    }
                }
                }
            },
            {
                "time": "2021-01-29T12:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1001.5,
                    "air_temperature": 2.9,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 92.6,
                    "wind_from_direction": 189.4,
                    "wind_speed": 2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 0.4
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 3.4
                    }
                }
                }
            },
            {
                "time": "2021-01-29T13:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1000.9,
                    "air_temperature": 2.9,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 95.5,
                    "wind_from_direction": 191.7,
                    "wind_speed": 2.3
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "heavyrain"
                    },
                    "details": {
                    "precipitation_amount": 1.2
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 3
                    }
                }
                }
            },
            {
                "time": "2021-01-29T14:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1000.1,
                    "air_temperature": 2.4,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 96.5,
                    "wind_from_direction": 179.6,
                    "wind_speed": 1.7
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrainshowers_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "heavyrain"
                    },
                    "details": {
                    "precipitation_amount": 1.3
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 1.8
                    }
                }
                }
            },
            {
                "time": "2021-01-29T15:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 999.4,
                    "air_temperature": 2.1,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 97.1,
                    "wind_from_direction": 180.9,
                    "wind_speed": 2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "lightrainshowers_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "rain"
                    },
                    "details": {
                    "precipitation_amount": 0.5
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "lightrain"
                    },
                    "details": {
                    "precipitation_amount": 0.5
                    }
                }
                }
            },
            {
                "time": "2021-01-29T16:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.8,
                    "air_temperature": 2.4,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 96.1,
                    "wind_from_direction": 196.8,
                    "wind_speed": 3
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-29T17:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.2,
                    "air_temperature": 3.5,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 94.3,
                    "wind_from_direction": 223.1,
                    "wind_speed": 3.8
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-29T18:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998,
                    "air_temperature": 3.7,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 93,
                    "wind_from_direction": 238,
                    "wind_speed": 3.9
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-29T19:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 997.8,
                    "air_temperature": 3.4,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 90.7,
                    "wind_from_direction": 253.5,
                    "wind_speed": 3.6
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-29T20:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 997.8,
                    "air_temperature": 3.5,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 87.6,
                    "wind_from_direction": 270.3,
                    "wind_speed": 3.8
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-29T21:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.1,
                    "air_temperature": 4.1,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 86.4,
                    "wind_from_direction": 279.8,
                    "wind_speed": 4
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-29T22:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.1,
                    "air_temperature": 4.1,
                    "cloud_area_fraction": 99.2,
                    "relative_humidity": 86.5,
                    "wind_from_direction": 281.3,
                    "wind_speed": 4.4
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "fair_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-29T23:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.3,
                    "air_temperature": 4,
                    "cloud_area_fraction": 97.7,
                    "relative_humidity": 87,
                    "wind_from_direction": 280.9,
                    "wind_speed": 4.7
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "fair_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "fair_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T00:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.5,
                    "air_temperature": 4,
                    "cloud_area_fraction": 93.8,
                    "relative_humidity": 86.9,
                    "wind_from_direction": 284.2,
                    "wind_speed": 4.9
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "fair_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "fair_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "fair_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T01:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.7,
                    "air_temperature": 3.8,
                    "cloud_area_fraction": 33.6,
                    "relative_humidity": 87.1,
                    "wind_from_direction": 289.2,
                    "wind_speed": 4.6
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "fair_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "clearsky_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "fair_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T02:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.9,
                    "air_temperature": 3.8,
                    "cloud_area_fraction": 2.3,
                    "relative_humidity": 86.9,
                    "wind_from_direction": 289.7,
                    "wind_speed": 4.5
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "clearsky_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "fair_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T03:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.9,
                    "air_temperature": 3.6,
                    "cloud_area_fraction": 1.6,
                    "relative_humidity": 86.7,
                    "wind_from_direction": 285.9,
                    "wind_speed": 4.2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "clearsky_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "fair_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T04:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 999,
                    "air_temperature": 3.2,
                    "cloud_area_fraction": 0.8,
                    "relative_humidity": 87.2,
                    "wind_from_direction": 281,
                    "wind_speed": 3.8
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "fair_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "fair_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T05:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 999.1,
                    "air_temperature": 2.9,
                    "cloud_area_fraction": 14.1,
                    "relative_humidity": 87.2,
                    "wind_from_direction": 271.5,
                    "wind_speed": 3.6
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_night"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "fair_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T06:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 999.6,
                    "air_temperature": 2.5,
                    "cloud_area_fraction": 44.5,
                    "relative_humidity": 88.2,
                    "wind_from_direction": 258.2,
                    "wind_speed": 3.2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T07:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1000,
                    "air_temperature": 3.3,
                    "cloud_area_fraction": 44.5,
                    "relative_humidity": 87.5,
                    "wind_from_direction": 255.4,
                    "wind_speed": 3.7
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "fair_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T08:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1000,
                    "air_temperature": 4.6,
                    "cloud_area_fraction": 34.4,
                    "relative_humidity": 84.4,
                    "wind_from_direction": 255.1,
                    "wind_speed": 4.4
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "clearsky_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T09:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 999.9,
                    "air_temperature": 6.4,
                    "cloud_area_fraction": 5.5,
                    "relative_humidity": 80.1,
                    "wind_from_direction": 253.4,
                    "wind_speed": 4.4
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "clearsky_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T10:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 999.9,
                    "air_temperature": 8.4,
                    "cloud_area_fraction": 4.7,
                    "relative_humidity": 72.1,
                    "wind_from_direction": 248.9,
                    "wind_speed": 4.2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T11:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 999.2,
                    "air_temperature": 9.9,
                    "cloud_area_fraction": 63.3,
                    "relative_humidity": 65.7,
                    "wind_from_direction": 243.8,
                    "wind_speed": 4.7
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T12:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.4,
                    "air_temperature": 9.9,
                    "cloud_area_fraction": 96.1,
                    "relative_humidity": 65.2,
                    "wind_from_direction": 225.7,
                    "wind_speed": 4.5
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T13:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 997.5,
                    "air_temperature": 9.6,
                    "cloud_area_fraction": 85.9,
                    "relative_humidity": 63.4,
                    "wind_from_direction": 231.2,
                    "wind_speed": 4.9
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T14:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 997,
                    "air_temperature": 9.5,
                    "cloud_area_fraction": 85.2,
                    "relative_humidity": 61.7,
                    "wind_from_direction": 240.4,
                    "wind_speed": 4.2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T15:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 997.1,
                    "air_temperature": 8.9,
                    "cloud_area_fraction": 95.3,
                    "relative_humidity": 55.1,
                    "wind_from_direction": 258.8,
                    "wind_speed": 4
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T16:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 997.6,
                    "air_temperature": 7.1,
                    "cloud_area_fraction": 96.1,
                    "relative_humidity": 60,
                    "wind_from_direction": 259.9,
                    "wind_speed": 3.3
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T17:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 998.6,
                    "air_temperature": 6.4,
                    "cloud_area_fraction": 98.4,
                    "relative_humidity": 65,
                    "wind_from_direction": 299.9,
                    "wind_speed": 4
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T18:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 999.6,
                    "air_temperature": 4.4,
                    "cloud_area_fraction": 90.6,
                    "relative_humidity": 79.5,
                    "wind_from_direction": 318.3,
                    "wind_speed": 5.2
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T19:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1000.4,
                    "air_temperature": 2.8,
                    "cloud_area_fraction": 96.9,
                    "relative_humidity": 77.5,
                    "wind_from_direction": 316.9,
                    "wind_speed": 4.3
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T20:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1001,
                    "air_temperature": 1.5,
                    "cloud_area_fraction": 91.4,
                    "relative_humidity": 83.6,
                    "wind_from_direction": 324.5,
                    "wind_speed": 3.6
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T21:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1001.4,
                    "air_temperature": 0.7,
                    "cloud_area_fraction": 97.7,
                    "relative_humidity": 84.4,
                    "wind_from_direction": 341.6,
                    "wind_speed": 4.1
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-30T22:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1001.8,
                    "air_temperature": 0.3,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 84.9,
                    "wind_from_direction": 356.2,
                    "wind_speed": 4.1
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                }
                }
            },
            {
                "time": "2021-01-30T23:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1002.3,
                    "air_temperature": 0.4,
                    "cloud_area_fraction": 99.2,
                    "relative_humidity": 69.6,
                    "wind_from_direction": 10.8,
                    "wind_speed": 3.9
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                }
                }
            },
            {
                "time": "2021-01-31T00:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1003.2,
                    "air_temperature": 0.2,
                    "cloud_area_fraction": 99.2,
                    "relative_humidity": 67.4,
                    "wind_from_direction": 16.3,
                    "wind_speed": 2.7
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                }
                }
            },
            {
                "time": "2021-01-31T01:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1003.9,
                    "air_temperature": 0.1,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 67.6,
                    "wind_from_direction": 18.8,
                    "wind_speed": 3
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                }
                }
            },
            {
                "time": "2021-01-31T02:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1004.3,
                    "air_temperature": -0.1,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 67.4,
                    "wind_from_direction": 26.7,
                    "wind_speed": 3.1
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                }
                }
            },
            {
                "time": "2021-01-31T03:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1004.6,
                    "air_temperature": -0.1,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 68.8,
                    "wind_from_direction": 54.9,
                    "wind_speed": 3
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                }
                }
            },
            {
                "time": "2021-01-31T04:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1005.2,
                    "air_temperature": -0.5,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 69,
                    "wind_from_direction": 77.7,
                    "wind_speed": 3.3
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                }
                }
            },
            {
                "time": "2021-01-31T05:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1006.2,
                    "air_temperature": -0.8,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 67.5,
                    "wind_from_direction": 86.3,
                    "wind_speed": 3.4
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0.1
                    }
                }
                }
            },
            {
                "time": "2021-01-31T06:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1006.7,
                    "air_temperature": -1.1,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 69,
                    "wind_from_direction": 75.2,
                    "wind_speed": 3.4
                    }
                },
                "next_12_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                },
                "next_6_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-31T07:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1007.1,
                    "air_temperature": -1,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 69.6,
                    "wind_from_direction": 71.3,
                    "wind_speed": 3.5
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-31T08:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1007.5,
                    "air_temperature": -0.6,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 67.3,
                    "wind_from_direction": 73.9,
                    "wind_speed": 3.7
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-31T09:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1007.3,
                    "air_temperature": 0,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 66.2,
                    "wind_from_direction": 68.8,
                    "wind_speed": 4.6
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-31T10:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1007.4,
                    "air_temperature": 1.2,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 60.6,
                    "wind_from_direction": 71.6,
                    "wind_speed": 4.7
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "partlycloudy_day"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-31T11:00:00Z",
                "data": {
                "instant": {
                    "details": {
                    "air_pressure_at_sea_level": 1006.8,
                    "air_temperature": 1.7,
                    "cloud_area_fraction": 100,
                    "relative_humidity": 56.7,
                    "wind_from_direction": 63.6,
                    "wind_speed": 4.9
                    }
                },
                "next_1_hours": {
                    "summary": {
                    "symbol_code": "cloudy"
                    },
                    "details": {
                    "precipitation_amount": 0
                    }
                }
                }
            },
            {
                "time": "2021-01-31T12:00:00Z",
                "data": {
                    "instant": {
                        "details": {
                        "air_pressure_at_sea_level": 1006.6,
                        "air_temperature": 2.1,
                        "cloud_area_fraction": 100,
                        "relative_humidity": 52,
                        "wind_from_direction": 64.5,
                        "wind_speed": 4.7
                        }
                    },
                    "next_12_hours": {
                        "summary": {
                        "symbol_code": "cloudy"
                        }
                    },
                    "next_6_hours": {
                        "summary": {
                        "symbol_code": "cloudy"
                        },
                        "details": {
                        "precipitation_amount": 0
                        }
                    }
                }
            }
            ]
        }
        }"""
        return response
