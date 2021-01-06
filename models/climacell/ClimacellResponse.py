from datetime import datetime
from backports.zoneinfo import ZoneInfo
from models.AppConstants import AppConstants


class ClimacellResponse(object):
    def __init__(self, precipitation_probability, temp,
                 precipitation_type,
                 weather_code, observation_time):
        self.temp: int = int(temp)
        self.precipitation_type: str = precipitation_type
        self.precipitation_probability: int = precipitation_probability
        self.weather_code: str = str(weather_code)
        self.observation_time: datetime = (datetime.fromisoformat(observation_time.replace("Z", "+00:00")))\
            .astimezone(ZoneInfo(AppConstants.local_time_zone))

def climacell_response_decoder(obj):
    if 'values' in obj:
        return ClimacellResponse(
            obj['values']['precipitationProbability'],
            obj['values']['temperature'],
            obj['values']['precipitationType'],
            obj['values']['weatherCode'],
            obj['startTime'])  # results are in GMT(UTC) time
    return obj
