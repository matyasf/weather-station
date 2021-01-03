import string
from datetime import datetime


class Utils:

    @staticmethod
    def log(msg: string) -> None:
        print(str(datetime.now()) + " " + msg)