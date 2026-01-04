# weather-station

Code for a weather station running on Raspberry Pi.

It uses a Bosch BME680 sensor [from pimoroni](https://shop.pimoroni.com/products/bme680-breakout) and a [waveshare 6" e-paper](https://www.waveshare.com/wiki/6inch_e-Paper_HAT).

### Installation

Make a virtual env: `python -m venv myenv` and then `source myenv/bin/activate`.

You need to have the [IT8951 library](https://github.com/GregDMeyer/IT8951) locally on the pi, since its not on [pypi.org](https://pypi.org/). To install run `pip install -e "git+https://github.com/GregDMeyer/IT8951#egg=IT8951"`

Install dependencies `pip install -r requirements.txt`

### Running the app

Run `python main.py`.

(if you enable TADO integration) On the first startup check the console to set up access to your TADO API.

#### Running on startup:

You can set it to auto-run on startup e.g. cron:

- Log in as the user you want to run it.
- run `crontab -e` and enter here: `@reboot cd /home/[PATH_TO_REPO]/weather-station/ && ./start_app.sh` (set it to executable with `chmod +x`, debug with `journalctl -u cron.service`)


### Testing locally

You can test it locally on a Unix machine (maybe on OSX too) by following the instructions in the [IT8951 repo](https://github.com/GregDMeyer/IT8951#readme)

### Common errors

- If you get an error when installing `RPi.GPIO`: `fatal error: Python.h: No such file or directory` then you will need to run `sudo apt install python3-dev`

- No such file or directory: `/dev/i2c-1`: Run `sudo raspi-config` and go to `Interfacing Options → I2C → Enable`

- No such file or directory: `/dev/spidev0.0`: Run `sudo raspi-config` and go to `Interfacing Options → SPI → Enable`

### Legal stuff

Weather forecast provided by [Climacell](https://www.climacell.co/) and [yr.no](https://www.yr.no), icons from [yr.no](http://nrkno.github.io/yr-weather-symbols/)

yr.no icons is under [CC 4.0 BY and MIT license](https://api.met.no/doc/License)

#### License

[Apache 2.0](http://www.apache.org/licenses/LICENSE-2.0)
