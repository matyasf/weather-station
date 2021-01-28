
class AppConstants:
    # yr.no API wants these in maximum 4 digits precision
    forecast_lat = 47.5249
    forecast_lon = 19.0825

    # climacell returns forecast in UTC, this is needed to convert it to local time
    local_time_zone = "Europe/Budapest"
    # https://www.climacell.co/weather-api/ Climacell allows 1000 calls/day = 0.7 calls/min
    # 100 calls/day = 4 calls/hour for air quality
    weather_api_refresh_secs = 50 * 60 # mins * seconds_in_a_minute
    bme680_refresh_secs = 5
    # see https://github.com/pimoroni/bme680-python/issues/11
    bme680_temperature_offset = -4

