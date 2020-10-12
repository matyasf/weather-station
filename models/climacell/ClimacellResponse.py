from datetime import datetime
from backports.zoneinfo import ZoneInfo
from models.AppConstants import AppConstants


class ClimacellResponse(object):
    def __init__(self, lat, lon, temp,
                 precipitation_type, precipitation_probability,
                 weather_code, observation_time):
        self.lat: float = lat
        self.lon: float = lon
        self.temp: int = int(temp)
        self.precipitation_type: str = precipitation_type
        self.precipitation_probability: int = precipitation_probability
        self.weather_code: str = weather_code
        self.observation_time: datetime = (datetime.fromisoformat(observation_time.replace("Z", "+00:00")))\
            .astimezone(ZoneInfo(AppConstants.local_time_zone))


def climacell_response_decoder(obj):
    if 'observation_time' in obj:
        return ClimacellResponse(
            obj['lat'],
            obj['lon'],
            obj['temp']['value'],
            obj['precipitation_type']['value'],
            obj['precipitation_probability']['value'],
            obj['weather_code']['value'],
            obj['observation_time']['value'])  # results are in GMT(UTC) time
    return obj


# sample response:
# response = """
#    [{"lat":47.524862,"lon":19.082513,
#     "temp":{"value":7.27,"units":"C"},
#     "precipitation_type":{"value":"rain"},
#     "precipitation_probability":{"value":65,"units":"%"},
#     "weather_code":{"value":"drizzle"},
#     "observation_time":{"value":"2020-10-13T17:00:00.000Z"}}, ...]
#  """
