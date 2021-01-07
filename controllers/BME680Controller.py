import bme680
from IT8951.display import AutoDisplay
from PIL import ImageFont, ImageDraw

from Utils import Utils
from models import AppConstants


class BME680Controller:

    def __init__(self):
        try:
            self.sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
        except IOError:
            self.sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)
        if self.sensor is None:
            Utils.log("could not init BME680 sensor!")
        self.font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 100)
        self.sensor.set_temp_offset(AppConstants.AppConstants.bme680_temperature_offset)
        self.sensor.set_humidity_oversample(bme680.OS_2X)
        self.sensor.set_pressure_oversample(bme680.OS_4X)
        self.sensor.set_temperature_oversample(bme680.OS_8X)
        self.sensor.set_filter(bme680.FILTER_SIZE_3)
        self.sensor.set_gas_status(bme680.DISABLE_GAS_MEAS)
        self.sensor.set_gas_status(bme680.DISABLE_HEATER)
        # self.sensor.set_gas_heater_temperature(320)
        # self.sensor.set_gas_heater_duration(150)
        # self.sensor.select_gas_heater_profile(0)

    def display_sensor_data(self, display: AutoDisplay) -> None:
        if self.sensor is None:
            pass
        text_y_start = 210
        if self.sensor.get_sensor_data() is False:
            Utils.log("could not get sensor data!")
        image_draw = ImageDraw.Draw(display.frame_buf)
        display.frame_buf.paste(0xFF, box=(5, text_y_start, 780, text_y_start + 140))
        image_draw.text((10, text_y_start),
                        text="{:.1f}".format(self.sensor.data.temperature) + "°C", font=self.font)
        image_draw.text((420, text_y_start),
                        text="{:.1f}".format(self.sensor.data.humidity) + "%", font=self.font)
        # if self.sensor.data.heat_stable: This is for the gas sensor