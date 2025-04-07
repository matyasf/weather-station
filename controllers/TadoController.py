from libtado.api import Tado
import traceback
from PIL import ImageFont, ImageDraw
from IT8951.display import AutoDisplay
from Utils import Utils
import concurrent.futures
from asyncio import Future
from models.AppConstants import AppConstants
from requests.exceptions import RequestException

class TadoController:
    """
    This class downloads and displays data from Tado smart devices.
    https://github.com/germainlefebvre4/libtado#usage
    """
    def __init__(self):
        self.tado_data: list[TadoData] = None
        self.font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 32)
        self.large_font = ImageFont.truetype("assets/IBMPlexSans-Medium.ttf", 52)
        self.error_msg: str = None
        self.tado: Tado = None
        try:
            self.tado = Tado(token_file_path='./libtado_refresh_token.json')
            status = self.tado.get_device_activation_status()
            if status == "PENDING":
                url = self.tado.get_device_verification_url()
                self.error_msg = 'TADO needs manual login via console :/ ' + url
                # to auto-open the browser (on a desktop device), un-comment the following line:
                # webbrowser.open_new_tab(url)
                self.tado.device_activation()
                status = self.tado.get_device_activation_status()
            if status == "COMPLETED":
                Utils.log("Tado login successful")
            else:
                Utils.log(f"Tado login status is {status}")
                self.error_msg = f"Tado login status is {status}"
        except RequestException as err:
            errs = "Tado error:" + str(err)
            self.error_msg = '\n'.join(errs[i:i + 40] for i in range(0, len(errs), 40))
            Utils.log(errs)

    def fetch_heating_data(self):
        if self.tado == None:
            return # error in constructor
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fut = executor.submit(self.download_tado_data)
            fut.add_done_callback(self.on_future_complete)

    def download_tado_data(self) -> None:
        zones = self.tado.get_zones()
        zone_states = self.tado.get_zone_states()
        self.tado_data = []
        for key, value in zone_states['zoneStates'].items():
            dat = TadoData()
            dat.name = self.find_zone_name(zones, key)
            dat.current_temperature = format(value['sensorDataPoints']['insideTemperature']['celsius'], '.1f')
            dat.target_temperature = "N/A" # happens if heating is off
            if value and value['setting'] and value['setting']['temperature'] and value['setting']['temperature']['celsius']:
                dat.target_temperature = format(value['setting']['temperature']['celsius'], '.1f')
            if dat.name != 'Közlekedő': # this room is not interesting
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
        y_start = 415
        x_start = 10
        column_width = 195
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
            image_draw.text((x_start + num * column_width, y_start), text=data.name, font=self.font)
            image_draw.text((x_start + num * column_width, y_start + 40), text=data.current_temperature + "°C", font=self.large_font)
            image_draw.text((x_start + num * column_width, y_start + 110), text=data.target_temperature + "°C min", font=self.font)
            num = num + 1

class TadoData:
    def __init__(self) -> None:
        self.name:str = None
        self.current_temperature:str = None
        self.target_temperature:str = None