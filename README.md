# weather-station

Code for a weather station running on Raspberry Pi.

It uses a Bosch BME680 sensor [from pimoroni](https://shop.pimoroni.com/products/bme680-breakout) and a [waveshare 6" e-paper](https://www.waveshare.com/wiki/6inch_e-Paper_HAT).

### How to use

You need to have the [IT8951 library](https://github.com/GregDMeyer/IT8951) locally on the pi, since its not on pypi.org.

You can set it to auto-run on startup e.g. by putting this into `/etc/rc.local` on your pi:

```
cd /home/pi/CODE/weather-project/weather-station &&
sudo bash -c 'python -u main.py &>> /home/pi/CODE/weather-project/weather-station/log.txt' &
```

(put this before `exit 0`)

### Testing locally

You can test it locally on a Unix machine (maybe on OSX too) by following the instructions in the [IT8951 repo](https://github.com/GregDMeyer/IT8951#readme)

### Legal stuff

Weather forecast provided by [Climacell](https://www.climacell.co/) and [yr.no](https://www.yr.no), icons from [yr.no](http://nrkno.github.io/yr-weather-symbols/)

yr.no stuff is under [CC 4.0 BY and MIT license](https://api.met.no/doc/License)

#### License

[Apache 2.0](http://www.apache.org/licenses/LICENSE-2.0)
