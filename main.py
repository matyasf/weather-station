#!/usr/bin/env python3

import argparse
import sys
import socket
import time
from datetime import datetime, timedelta

from PIL import ImageFont, ImageDraw, Image
from IT8951.display import VirtualEPDDisplay, AutoEPDDisplay, AutoDisplay
from PIL.ImageFont import FreeTypeFont

from Utils import Utils
from controllers.BME680Controller import BME680Controller
from controllers.ClimacellController import ClimacellController
#from controllers.YrController import YrController
#from controllers.TadoController import TadoController
from IT8951 import constants
from models.AppConstants import AppConstants


def parse_args():
    p = argparse.ArgumentParser(description='Set EPD functionality')
    p.add_argument('-v', '--virtual', action='store_true',
                   help='display using a Tkinter window instead of the '
                        'actual e-paper device (for testing without a '
                        'physical device)')
    p.add_argument('-r', '--rotate', default=None, choices=['CW', 'CCW', 'flip'],
                   help='run the tests with the display rotated by the specified value')
    return p.parse_args()


def init_display(args) -> AutoDisplay:
    # display.frame_buf is a 8 bit pixel B&W image
    if not args.virtual:
        Utils.log('Initializing EPaper Display...')
        # here, spi_hz controls the rate of data transfer to the device, so a higher
        # value means faster display refreshes. the documentation for the IT8951 device
        # says the max is 24 MHz (24000000), but my device seems to still work as high as
        # 80 MHz (80000000)
        display_ref = AutoEPDDisplay(vcom=-2.06, rotate=args.rotate, spi_hz=24000000)
        #Utils.log('VCOM set to ' + str(display_ref.epd.get_vcom()))
    else:
        display_ref = VirtualEPDDisplay(dims=(800, 600), rotate=args.rotate)
        Utils.log("initializing virtual display")
    return display_ref


def refresh_time_text(display_ref: AutoDisplay, time_font: FreeTypeFont) -> None:
    y_pos = 0
    image_draw = ImageDraw.Draw(display_ref.frame_buf)
    image_draw.rectangle((5, y_pos + 5, 780, 250 + y_pos), fill=255) # black rectangle
    now = datetime.now()
    image_draw.text((5, y_pos-40), text=now.strftime("%H:%M"), font=time_font)

def draw_test_penguin(display_ref: AutoDisplay) -> None:
    #im2 = Image.new('L', (650, 500), 0xFF) # frame_buf
    #font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 100)
    #image_draw2.text((10, 10), text="12:32:54", font=font)
    #im2.save('test.png')
    display_ref.frame_buf.paste(0xFF, box=(0, 0, display_ref.width, display_ref.height))
    display_ref.draw_full(constants.DisplayModes.GC16)
    icon_bmp = Image.open("assets/test_penguin.png")
    icon_bmp.thumbnail((display_ref.width - 10, display_ref.height - 10))
    display_ref.frame_buf.paste(icon_bmp) # OK
    display_ref.draw_full(constants.DisplayModes.GC16)
    sleep(8)

def wait_for_internet(timeout=15):
    """Wait for internet connection with timeout."""
    print(f"Waiting for internet (max {timeout}s)...")
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            print("✓ Internet connected!")
            return
        except OSError:
            remaining = int(end_time - time.time())
            if remaining > 0:
                print(f"  Retrying... ({remaining}s remaining)")
            time.sleep(1)
    print("✗ Timeout: No internet connection")

def init() -> None:
    args = parse_args()

    climacell = ClimacellController()
    #tado = TadoController()
    #yr_no = YrController()
    bme680 = BME680Controller()
    display = init_display(args)
    display.draw_full(constants.DisplayModes.GC16)
    Utils.log("starting app")
    time_font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 280)
    last_weather_refresh_time = datetime.fromisoformat("2000-01-01")
    #last_tado_refresh_time = datetime.fromisoformat("2000-01-01")
    last_bme_refresh_time = datetime.fromisoformat("2000-01-01")
    last_full_refresh_time = datetime.now()

    refresh_time_text(display, time_font) # display the time until the internet loads
    display.draw_full(constants.DisplayModes.GC16)
    wait_for_internet() # can take up to 10 secs
    while True:
        now_time = datetime.now()
        refresh_time_text(display, time_font)
        if (last_weather_refresh_time + timedelta(seconds=AppConstants.weather_api_refresh_secs)) < now_time:
            last_weather_refresh_time = now_time
            climacell.fetch_weather()
            #yr_no.fetch_weather()
        #if (last_tado_refresh_time + timedelta(seconds=AppConstants.tado_refresh_secs)) < now_time:
            #last_tado_refresh_time = now_time
            #tado.fetch_heating_data()
        if (last_bme_refresh_time + timedelta(seconds=AppConstants.bme680_refresh_secs)) < now_time:
            last_bme_refresh_time = now_time
            bme680.display_sensor_data(display)
        if (last_full_refresh_time + timedelta(seconds=60*20)) < now_time:
            # do a full refresh sometimes, this removes small ghosting artifacts
            last_full_refresh_time = now_time
            display.draw_full(constants.DisplayModes.GC16)
        climacell.display_data_if_any(display)
        #yr_no.display_data_if_any(display)
        #tado.display_data_if_any(display)
        display.draw_partial(constants.DisplayModes.GL16)

        elapsed_time = datetime.now() - now_time
        if elapsed_time.total_seconds() < 2: # wait until 2 secods have elapsed before refresh
            sleep_duration = 2 - elapsed_time.total_seconds()
            #print(str(sleep_duration) + " secs slept")
            time.sleep(sleep_duration)
        sys.stdout.flush()

if __name__ == '__main__':
    #disp = init_display(parse_args())
    #draw_test_penguin(disp)
    init()
