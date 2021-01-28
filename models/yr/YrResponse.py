from datetime import datetime
try:
    from zoneinfo import ZoneInfo # TODO test for Pyton 3.9
except ImportError: # for Python < 3.9
    from backports.zoneinfo import ZoneInfo
from models.AppConstants import AppConstants


class YrResponse(object):
    def __init__(self, precipitation_amount, temp,
                 weather_code, observation_time):
        self.precipitation_amount: int = precipitation_amount
        self.temp: int = int(temp)
        self.weather_code: str = str(weather_code)
        self.observation_time: datetime = (datetime.fromisoformat(observation_time.replace("Z", "+00:00")))\
            .astimezone(ZoneInfo(AppConstants.local_time_zone))

def yr_response_decoder(obj):
    if 'time' in obj and 'data' in obj and 'next_1_hours' in obj['data']:
        # this returns tons of results, in later forecasts there is no 'next_1_hours'
        return YrResponse(
            obj['data']['next_1_hours']['details']['precipitation_amount'],
            obj['data']['instant']['details']['air_temperature'],
            obj['data']['next_1_hours']['summary']['symbol_code'],
            obj['time'])  # results are in GMT(UTC) time
    return obj
