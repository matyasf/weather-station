
class AppConstants:
    forecast_lat = 47.524862
    forecast_lon = 19.082513

    # climacell returns forecast in UTC, this is needed to convert it to local time
    local_time_zone = "Europe/Budapest"
    climacell_api_refresh_secs = 5
    bme680_refresh_secs = 4

