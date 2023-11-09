
class AppConstants:
    # yr.no API wants these in maximum 4 digits precision
    forecast_lat = 47.5951
    forecast_lon = 18.9519
    height_above_sea = 150 # in meters, yr.no API uses it
    # climacell returns forecast in UTC, this is needed to convert it to local time
    local_time_zone = "Europe/Budapest"
    # 100 calls/day = 4 calls/hour for air quality
    weather_api_refresh_secs = 50 * 60 # mins * seconds_in_a_minute
    bme680_refresh_secs = 15
    # see https://github.com/pimoroni/bme680-python/issues/11
    bme680_temperature_offset = -3.7
    tado_refresh_secs = 90
