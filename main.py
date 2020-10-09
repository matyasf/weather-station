import argparse
from sys import path
from time import sleep

from IT8951 import constants

path += ['../IT8951/IT8951']


def parse_args():
    p = argparse.ArgumentParser(description='Test EPD functionality')
    p.add_argument('-v', '--virtual', action='store_true',
                   help='display using a Tkinter window instead of the '
                        'actual e-paper device (for testing without a '
                        'physical device)')
    p.add_argument('-r', '--rotate', default=None, choices=['CW', 'CCW', 'flip'],
                   help='run the tests with the display rotated by the specified value')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if not args.virtual:
        from IT8951.display import AutoEPDDisplay
        print('Initializing EPD...')
        # here, spi_hz controls the rate of data transfer to the device, so a higher
        # value means faster display refreshes. the documentation for the IT8951 device
        # says the max is 24 MHz (24000000), but my device seems to still work as high as
        # 80 MHz (80000000)
        display = AutoEPDDisplay(vcom=-2.06, rotate=args.rotate, spi_hz=24000000)
        print('VCOM set to', display.epd.get_vcom())
    else:
        from IT8951.display import VirtualEPDDisplay
        display = VirtualEPDDisplay(dims=(800, 600), rotate=args.rotate)
        print("initializing virtual display")

    import requests

    # TEST
    url = "https://api.climacell.co/v3/weather/forecast/hourly"
    querystring = {"lat": "47.524862", "lon": "19.082513", "unit_system": "si", "start_time": "now",
                   "end_time": "2020-10-11T22:44:00Z", "fields": "precipitation_probability,temp,precipitation_type",
                   "apikey": "u0q4InQgQv6dd5scyrcwy9oP0w10G1yo"}
    response = requests.request("GET", url, params=querystring)
    print(response.text)

    # set frame buffer to gradient
    for i in range(16):
        color = i * 0x10
        box = (
            i * display.width // 16,  # xmin
            0,  # ymin
            (i + 1) * display.width // 16,  # xmax
            display.height  # ymax
        )
        display.frame_buf.paste(color, box=box)

    # update display
    display.draw_full(constants.DisplayModes.GC16)

    # then add some black and white bars on top of it, to test updating with DU on top of GC16
    box = (0, display.height // 5, display.width, 2 * display.height // 5)
    display.frame_buf.paste(0x00, box=box)

    box = (0, 3 * display.height // 5, display.width, 4 * display.height // 5)
    display.frame_buf.paste(0xF0, box=box)

    display.draw_partial(constants.DisplayModes.DU)
    sleep(1)
