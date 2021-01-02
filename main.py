import argparse
import sys
from time import sleep
from datetime import datetime, timedelta

from PIL import ImageFont, ImageDraw, Image
from IT8951.display import VirtualEPDDisplay, AutoEPDDisplay, AutoDisplay

from controllers.BME680Controller import BME680Controller
from controllers.ClimacellController import ClimacellController
from IT8951 import constants

from models.AppConstants import AppConstants


def parse_args():
    p = argparse.ArgumentParser(description='Test EPD functionality')
    p.add_argument('-v', '--virtual', action='store_true',
                   help='display using a Tkinter window instead of the '
                        'actual e-paper device (for testing without a '
                        'physical device)')
    p.add_argument('-r', '--rotate', default=None, choices=['CW', 'CCW', 'flip'],
                   help='run the tests with the display rotated by the specified value')
    return p.parse_args()


def init_display():
    # display.frame_buf is a 8 bit pixel B&W image
    if not args.virtual:
        print('Initializing EPD...')
        # here, spi_hz controls the rate of data transfer to the device, so a higher
        # value means faster display refreshes. the documentation for the IT8951 device
        # says the max is 24 MHz (24000000), but my device seems to still work as high as
        # 80 MHz (80000000)
        display = AutoEPDDisplay(vcom=-2.06, rotate=args.rotate, spi_hz=24000000)
        print('VCOM set to', display.epd.get_vcom())
    else:
        display = VirtualEPDDisplay(dims=(800, 600), rotate=args.rotate)
        print("initializing virtual display")
    return display


def refresh_time_text(display: AutoDisplay):
    image_draw = ImageDraw.Draw(display.frame_buf)
    image_draw.rectangle((5, 5, 780, 210), fill=255)
    now = datetime.now()
    image_draw.text((60, -55), text=now.strftime("%H:%M"), font=time_font)


def draw_test_penguin():
    #icon_bmp2 = Image.open("assets/test_penguin.png")
    #icon_bmp2 = Image.open("assets/yr_icons_100/01m.png")
    #icon_bmp2 = icon_bmp2.convert("L")
    im2 = Image.new('L', (650, 500), 0xFF) # frame_buf
    image_draw2 = ImageDraw.Draw(im2)
    #image_draw2.bitmap((0, 0), icon_bmp2)
    font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 100)
    image_draw2.text((10, 10), text="12:32:54", font=font)
    im2.save('test.png')

    display.frame_buf.paste(0xFF, box=(0, 0, display.width, display.height))
    icon_bmp = Image.open("assets/test_penguin.png")
    icon_bmp.thumbnail((display.width - 10, display.height - 10))
    display.frame_buf.paste(icon_bmp) # OK
    display.draw_full(constants.DisplayModes.GC16)
    sleep(8)

if __name__ == '__main__':
    args = parse_args()
    climacell = ClimacellController()
    bme680 = BME680Controller()
    display = init_display()
    display.draw_full(constants.DisplayModes.GC16)
    print("current time is: " + str(datetime.now()))
    time_font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 250)
    last_weather_refresh_time = datetime.fromisoformat("2000-01-01")
    last_bme_refresh_time = datetime.fromisoformat("2000-01-01")
    while True:
        now_time = datetime.now()
        refresh_time_text(display)
        if (last_weather_refresh_time + timedelta(seconds=AppConstants.climacell_api_refresh_secs)) < now_time:
            last_weather_refresh_time = now_time
            climacell.fetch_weather()
            print("refresh weather")
        if (last_bme_refresh_time + timedelta(seconds=AppConstants.bme680_refresh_secs)) < now_time:
            last_bme_refresh_time = now_time
            bme680.display_sensor_data(display)
            # print("refresh BME680 sensor")
        new_weather_data = climacell.display_data_if_any(display)
        # + code to get data from BME680
        display.draw_partial(constants.DisplayModes.GL16)

        elapsed_time = datetime.now() - now_time
        if elapsed_time.total_seconds() < 1:
            sleep_duration = 1 - elapsed_time.total_seconds() - 0.01
            # print("sleep " + str(sleep_duration) + " secs")
            sleep(sleep_duration)
        sys.stdout.flush()
