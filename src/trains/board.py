import os
from PIL import ImageFont

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

        # Display Chrome
        self.clock = Clock(self)
        self.clock.show()

        # Our scenes
        self.initialising = Initialising(self)
        self.noservices = NoServices(self)
        self.departureboard = DepartureBoard(self)

        self.tick_updates = [
            self.noservices,
            self.departureboard
        ]

        # Initial render
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
        print("Loading {0}".format(path))
        return ImageFont.truetype(path, size)
    
    def init_display(self):
        if Config.get("debug.dummy", False):
            self.device = dummy(width=256, height=64, rotate=0, mode="1")
        else:
            serial = spi()
            self.device = ssd1322(serial, mode="1", rotate=0)
        
        self.device.clear()
        self.viewport = viewport(self.device, width=self.device.width, height=self.device.height)
    
    def update_state(self, state):
        self.__newdata = state
    
    def update_data(self, timestamp, tick):

        # Tick Updates
        for scene in self.tick_updates:
            scene.update_tick(timestamp, tick)
        
        # Only care if data has changed
        if self.__newdata != self.__data:
            self.__data = self.__newdata
            self.initialising.hide()

            if len(self.__data.departures) == 0:
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