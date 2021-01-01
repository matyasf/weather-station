
class AppConstants:
    forecast_lat = 47.524862
    forecast_lon = 19.082513

    # climacell returns forecast in UTC, this is needed to convert it to local time
    local_time_zone = "Europe/Budapest"
    # https://www.climacell.co/weather-api/ Climacell allows 1000 calls/day = 0.7 calls/min
    # 100 calls/day = 4 calls/hour for air quality
    climacell_api_refresh_secs = 2400 # 2400 secs = 30 mins
    bme680_refresh_secs = 4

