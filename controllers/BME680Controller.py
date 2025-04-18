import bme680
from IT8951.display import AutoDisplay
from PIL import ImageFont, ImageDraw, Image

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
        #self.sensor.set_gas_status(bme680.DISABLE_GAS_MEAS)
        #self.sensor.set_gas_heater_temperature(320)
        #self.sensor.set_gas_heater_duration(150)
        #self.sensor.select_gas_heater_profile(0)

    def display_sensor_data(self, display: AutoDisplay) -> None:
        if self.sensor is None:
            pass
        text_y_start = 265
        if self.sensor.get_sensor_data() is False:
            Utils.log("could not get BME sensor data!")
        image_draw = ImageDraw.Draw(display.frame_buf)
        display.frame_buf.paste(0xFF, box=(5, text_y_start, 790, text_y_start + 105))
        self.draw_temp_and_humidity(image_draw, text_y_start, 60, 470)
        #if self.sensor.data.heat_stable:
        #    self.draw_temp_and_humidity(image_draw, text_y_start, 7, 305)
        #    self.draw_gas_resistance(text_y_start, image_draw, display)
        #else:
        #    self.draw_temp_and_humidity(image_draw, text_y_start, 60, 460)
    
    def draw_temp_and_humidity(self, image_draw, text_y_start: int, temp_text_x_start: int, humidity_text_x_start: int):
        image_draw.text((temp_text_x_start, text_y_start),
                        text="{:.1f}".format(self.sensor.data.temperature) + "°C", font=self.font)
        image_draw.text((humidity_text_x_start, text_y_start),
                        text=str(round(self.sensor.data.humidity)) + "%", font=self.font)

    def draw_gas_resistance(self, text_y_start, image_draw, display):
        air_quality = Image.open("assets/air_quality_icon.png")
        display.frame_buf.paste(air_quality, (530, text_y_start + 30))
        gas_resistance = round(self.sensor.data.gas_resistance) # gas resistance in Ohms ~1000 ... 100000++
        gas_resistance = round((gas_resistance / 45000) * 100) # 45000 is the baseline value
        Utils.log("gas resistance: " + str(gas_resistance))
        image_draw.text((595, text_y_start), text=str(gas_resistance), font=self.font)
