from datetime import datetime


class ClimacellResponse(object):
    def __init__(self, lat, lon, temp,
                 precipitation_type, precipitation_probability,
                 weather_code, observation_time):
        self.lat: float = lat
        self.lon: float = lon
        self.temp: float = temp
        self.precipitation_type: str = precipitation_type
        self.precipitation_probability: int = precipitation_probability
        self.weather_code: str = weather_code
        self.observation_time: datetime = datetime.fromisoformat(observation_time.replace("Z", "+00:00"))


def climacell_response_decoder(obj):
    if 'observation_time' in obj:
        return ClimacellResponse(
            obj['lat'],
            obj['lon'],
            obj['temp']['value'],
            obj['precipitation_type']['value'],
            obj['precipitation_probability']['value'],
            obj['weather_code']['value'],
            obj['observation_time']['value'])
    return obj