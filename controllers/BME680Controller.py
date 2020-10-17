import bme680
from IT8951.display import AutoDisplay
from PIL import ImageFont, ImageDraw


class BME680Controller:

    def __init__(self):
        try:
            self.sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
        except IOError:
            self.sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)
        if self.sensor is None:
            print("could not init sensor!")
        self.font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 100)
        self.sensor.set_humidity_oversample(bme680.OS_2X)
        self.sensor.set_pressure_oversample(bme680.OS_4X)
        self.sensor.set_temperature_oversample(bme680.OS_8X)
        self.sensor.set_filter(bme680.FILTER_SIZE_3)
        self.sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

        self.sensor.set_gas_heater_temperature(320)
        self.sensor.set_gas_heater_duration(150)
        self.sensor.select_gas_heater_profile(0)

    def display_sensor_data(self, display: AutoDisplay):
        if self.sensor is None:
            pass
        text_y_start = 210
        if self.sensor.get_sensor_data() is False:
            print("could not get sensor data!")
        image_draw = ImageDraw.Draw(display.frame_buf)
        display.frame_buf.paste(0xFF, box=(5, text_y_start, 780, text_y_start + 140))
        image_draw.text((10, text_y_start),
                        text=str(self.sensor.data.temperature) + "°C", font=self.font)
        image_draw.text((380, text_y_start),
                        text=str(self.sensor.data.humidity) + "%", font=self.font)

        if self.sensor.data.heat_stable:
            print('sensor.data.gas_resistance: ' + str(self.sensor.data.gas_resistance))
        else:
            print("heat data is not stable (yet?)")
