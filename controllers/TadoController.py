import libtado.api
import traceback
from PIL import ImageFont, ImageDraw
from IT8951.display import AutoDisplay
from Utils import Utils
import concurrent.futures
from asyncio import Future
from models.AppConstants import AppConstants


class TadoController:
    """
    This class downloads and displays data from Tado smart devices.
    https://github.com/germainlefebvre4/libtado#usage
    """
    def __init__(self):
        self.tado = libtado.api.Tado(AppConstants.tado_username, AppConstants.tado_password, AppConstants.tado_secret)
        self.tado_data = None
        self.font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 38)
        self.large_font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 65)
        self.error_msg = None

    def fetch_heating_data(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fut = executor.submit(self.download_tado_data)
            fut.add_done_callback(self.on_future_complete)

    def download_tado_data(self) -> None:
        zones = self.tado.get_zones()
        zone_states = self.tado.get_zone_states()
        self.tado_data = []
        for key, value in zone_states['zoneStates'].items():
            dat = {}
            dat['name'] = self.find_zone_name(zones, key)
            dat['current_temperature'] = format(value['sensorDataPoints']['insideTemperature']['celsius'], '.1f')
            dat['target_temperature'] = "N/A" # happens if heating is off
            if value and value['setting'] and value['setting']['temperature'] and value['setting']['temperature']['celsius']:
                dat['target_temperature'] = format(value['setting']['temperature']['celsius'], '.1f')
            self.tado_data.append(dat)

    def find_zone_name(self, zones, id) -> str:
        for item in zones:
            if str(item['id']) == str(id):
                return item['name']
        self.error_msg = 'Cannot find ' + str(id) + ' in ' + str(zones)
        return "undefined"

    def on_future_complete(self, future: Future) -> None:
        if future.exception():
            self.error_msg = ":( Tado: " + repr(future.exception())
            self.error_msg = '\n'.join(self.error_msg[i:i + 40] for i in range(0, len(self.error_msg), 40))
            Utils.log("TadoController raised error:\n" + "".join(traceback.TracebackException.from_exception(future.exception()).format()))
            self.tado_data = None
        else:
            self.error_msg = None

    def display_data_if_any(self, display: AutoDisplay):
        y_start = 390
        column_width = 250
        if self.error_msg:
            image_draw = ImageDraw.Draw(display.frame_buf)
            display.frame_buf.paste(0xFF, box=(5, y_start, 790, y_start + 245))
            image_draw.multiline_text((5, y_start), text=self.error_msg, font=self.font)
            return
        if self.tado_data is None:
            return
        image_draw = ImageDraw.Draw(display.frame_buf)
        display.frame_buf.paste(0xFF, box=(5, y_start, 790, y_start + 245))
        num = 0
        for data in self.tado_data:
            image_draw.text((10 + num * column_width, y_start), text=str(data['name']), font=self.font)
            image_draw.text((10 + num * column_width, y_start + 50), text=str(data['current_temperature'])+ "°C", font=self.large_font)
            image_draw.text((10 + num * column_width, y_start + 130), text=str(data['target_temperature'])+ "°C min", font=self.font)
            num = num + 1