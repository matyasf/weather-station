# **************************************************************************
# https://steemit.com/steemstem/@procrastilearner/killing-time-with-recreational-math-calculate-sunrise-and-sunset-times-using-python
# This code is released by Procrastilearner under the CC BY-SA 4.0 license.
#
# Source for the sunrise calculation:
#     https://en.wikipedia.org/wiki/Sunrise_equation
# **************************************************************************
import datetime
import math

class SunriseSunsetCalculator:
    jd2000 = 2451545  # the julian date for Jan 1 2000 at noon

    @classmethod
    def date_to_jd(cls, year: int, month: int, day: int) -> float:
        # Convert a date to Julian Day.
        # Algorithm from 'Practical Astronomy with your Calculator or Spreadsheet',
        # 4th ed., Duffet-Smith and Zwart, 2011.
        # This function extracted from https://gist.github.com/jiffyclub/1294443
        if month == 1 or month == 2:
            yearp = year - 1
            monthp = month + 12
        else:
            yearp = year
            monthp = month
        # this checks where we are in relation to October 15, 1582, the beginning
        # of the Gregorian calendar.
        if ((year < 1582) or
            (year == 1582 and month < 10) or
            (year == 1582 and month == 10 and day < 15)):
            # before start of Gregorian calendar
            B = 0
        else:
            # after start of Gregorian calendar
            A = math.trunc(yearp / 100.)
            B = 2 - A + math.trunc(A / 4.)

        if yearp < 0:
            C = math.trunc((365.25 * yearp) - 0.75)
        else:
            C = math.trunc(365.25 * yearp)
        D = math.trunc(30.6001 * (monthp + 1))
        jd = B + C + D + day + 1720994.5
        return jd

    # some sample values:
    # latitude_deg = 43.65
    # longitude_deg = -79.38
    # timezone = -4.0  # Daylight Savings Time is in effect, this would be -5 for winter time
    @staticmethod
    def calculate_sunrise(latitude_deg: float, longitude_deg: float, timezone: int) -> datetime:
        (Jtransit, omega_degrees) = SunriseSunsetCalculator.do_calculations(latitude_deg, longitude_deg)

        Jrise = Jtransit - omega_degrees/360
        numdays = Jrise - SunriseSunsetCalculator.jd2000
        numdays =  numdays + 0.5 #offset because Julian dates start at noon
        numdays =  numdays + timezone/24 #offset for time zone
        return datetime.datetime(2000, 1, 1) + datetime.timedelta(numdays)

    @staticmethod
    def calculate_sunset(latitude_deg: float, longitude_deg: float, timezone: int) -> datetime:
        (Jtransit, omega_degrees) = SunriseSunsetCalculator.do_calculations(latitude_deg, longitude_deg)

        Jset = Jtransit + omega_degrees/360
        numdays = Jset - SunriseSunsetCalculator.jd2000
        numdays =  numdays + 0.5 #offset because Julian dates start at noon
        numdays =  numdays + timezone/24 #offset for time zone
        return datetime.datetime(2000, 1, 1) + datetime.timedelta(numdays)

    @classmethod
    def do_calculations(cls, latitude_deg: float, longitude_deg: float):
        pi = 3.14159265359
        latitude_radians = math.radians(latitude_deg)

        currentDT = datetime.datetime.now()
        current_year = currentDT.year
        current_month = currentDT.month
        current_day = currentDT.day

        jd_now = SunriseSunsetCalculator.date_to_jd(current_year, current_month, current_day)
        n = jd_now - SunriseSunsetCalculator.jd2000 + 0.0008
        jstar = n - longitude_deg/360
        M_deg = (357.5291 + 0.98560028 * jstar)%360
        M = M_deg * pi/180
        C = 1.9148 * math.sin(M) + 0.0200 * math.sin(2*M) + 0.0003 * math.sin(3*M)
        lamda_deg = math.fmod(M_deg + C + 180 + 102.9372,360)
        lamda = lamda_deg * pi/180
        Jtransit = 2451545.5 + jstar + 0.0053 * math.sin(M) - 0.0069 * math.sin(2*lamda)
        earth_tilt_deg = 23.44
        earth_tilt_rad = math.radians(earth_tilt_deg)
        sin_delta = math.sin(lamda) * math.sin(earth_tilt_rad)
        angle_delta = math.asin(sin_delta)
        sun_disc_deg =  -0.83
        sun_disc_rad = math.radians(sun_disc_deg)
        cos_omega = (math.sin(sun_disc_rad) - math.sin(latitude_radians) * math.sin(angle_delta))/(math.cos(latitude_radians) * math.cos(angle_delta))
        omega_radians = math.acos(cos_omega)
        omega_degrees = math.degrees(omega_radians)
        return (Jtransit, omega_degrees)