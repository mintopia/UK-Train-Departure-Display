import os
from PIL import ImageFont
from datetime import time as dtt, datetime

from trains.config import Config
from trains.elements import *
from trains.scenes import *
import trains.utils as utils

from luma.core.interface.serial import spi
from luma.core.device import dummy
from luma.core.render import canvas
from luma.oled.device import ssd1322
from luma.core.virtual import viewport, snapshot, hotspot

class Board:
    hotspots = {}
    elements = {}

    def __init__(self):
        self.__data = None
        self.__newdata = None

        self.load_fonts()
        self.init_display()
        self.init_powersaving()
        self.tick_updates = []

    def init_powersaving(self):
        self.brightness = Config.get("settings.brightness")
        self.normal_brightness = self.brightness

        start = Config.get("settings.powersaving.start", "01:00")
        end = Config.get("settings.powersaving.end", "07:00")
        self.powersaving_brightness = Config.get("settings.powersaving.brightness", 0)
        
        self.powersaving_start = dtt(hour=int(start[:2]), minute=int(start[3:5]))
        self.powersaving_end = dtt(hour=int(end[:2]), minute=int(end[3:5]))

        self.update_powersaving(datetime.now())

    def update_powersaving(self, timestamp):
        if not self.powersaving_start or not self.powersaving_end:
            return

        powersaving = False
        now = timestamp.time()
        if self.powersaving_start <= self.powersaving_end:
            # eg: 00:00 - 07:00
            if self.powersaving_start <= now < self.powersaving_end:
                powersaving = True
        elif now >= self.powersaving_start or now < self.powersaving_end:
            # eg: 22:00 - 06:00
            powersaving = True
        
        if powersaving and self.brightness != self.powersaving_brightness:
            self.set_brightness(self.powersaving_brightness)
        elif not powersaving and self.brightness != self.normal_brightness:
            self.set_brightness(self.normal_brightness)

    
    def departure_board(self):
        # Our scenes
        self.clock = Clock(self)
        self.initialising = Initialising(self)
        self.noservices = NoServices(self)
        self.departureboard = DepartureBoard(self)

        self.tick_updates.append(self.noservices)
        self.tick_updates.append(self.departureboard)

        self.initialising.show()
        self.viewport.refresh()
        self.show_image()
    
    def load_fonts(self):
        self.fonts = {
            "regular": self.load_font("Dot Matrix Regular.ttf", 10),
            "bold": self.load_font("Dot Matrix Bold.ttf", 10),
            "boldtall": self.load_font("Dot Matrix Bold Tall.ttf", 10),
            "boldlarge": self.load_font("Dot Matrix Bold.ttf", 20)
        }
    
    def load_font(self, font, size):
        path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                '../'
                'fonts',
                font
            )
        )
        return ImageFont.truetype(path, size)
    
    def init_display(self):
        if Config.get("debug.dummy", False):
            self.device = dummy(width=256, height=64, rotate=0, mode="1")
        else:
            serial = spi(bus_speed_hz=32000000)
            self.device = ssd1322(serial, mode="1", rotate=0)
        
        self.viewport = viewport(self.device, width=self.device.width, height=self.device.height)
    
    def update_state(self, state):
        self.__newdata = state
    
    def set_brightness(self, value):
        self.brightness = value
        self.device.contrast(value)
    
    def update_data(self, timestamp, tick):
        # Tick Updates
        for scene in self.tick_updates:
            scene.update_tick(timestamp, tick)
        
        # Only care if data has changed
        if self.__newdata != self.__data:
            self.__data = self.__newdata
            self.initialising.hide()
            self.clock.show()

            if len(self.__data["departures"]) == 0:
                self.departureboard.hide()
                self.noservices.update_state(self.__data)
                self.noservices.show()
            else:
                self.noservices.hide()
                self.departureboard.update_state(self.__data)
                self.departureboard.show()
    
    def render(self, timestamp, ticks):
        self.viewport.refresh()
        self.show_image()
        return
    
    def show_image(self):
        if not Config.get("debug.dummy", False):
            return
        
        utils.display_image("Departure Board", self.device.image)