import trains.elements as elements
from trains.config import Config

from trains.utils import wordwrap, ordinal

from datetime import datetime, timedelta
from pprint import pprint
import math

class SceneElement:
    def __init__(self, code, hotspot, location=(0, 0), visible=True):
        self.code = code
        self.location = location
        self.hotspot = hotspot
        self.visible = visible
        self.added = False
    
    def show(self, viewport):
        if self.added:
            return
        
        self.added = True
        viewport.add_hotspot(self.hotspot, self.location)

    def hide(self, viewport):
        self.added = False
        try:
            viewport.remove_hotspot(self.hotspot, self.location)
        except ValueError:
            pass


class Scene:
    def __init__(self, board, state=None):
        self.board = board
        self.elements = {}
        self.setup()
        if state:
            self.update_state(state)
    
    def add_text(self, code, width=256, height=12, font=None, location=(0, 0), align="left", text="", visible=True):
        if not font:
            font = self.board.fonts["regular"]
        
        if code in self.elements:
            raise RuntimeError("The code has already been added")
        
        hotspot = elements.StaticText(width, height, font, self.board.device.mode, text=text, align=align, interval=0.02)
        return self.add_element(code, hotspot, location, visible)
    
    def add_element(self, code, hotspot, location=(0,0), visible=True):
        element = SceneElement(code, hotspot, location, visible)
        self.elements[code] = element
        return element
    
    def get_elements(self):
        return self.elements.values()
    
    def get_element(self, code):
        if code not in self.elements:
            return None
        return self.elements[code]
    
    def update_state(self, state):
        return
    
    def update_tick(self, timestamp, tick):
        return
    
    def setup(self):
        return
    
    def show(self):
        for element in self.elements.values():
            if element.visible:
                element.show(self.board.viewport)
    
    def hide(self):
        for element in self.elements.values():
            element.hide(self.board.viewport)

class Clock(Scene):
    def setup(self):
        hotspot = elements.Clock(256, 14, self.board.fonts, interval=0.1)
        self.add_element("clock", hotspot, (0, 50))

class Initialising(Scene):
    def setup(self):
        self.add_text("initialising", text="Departure board is initialising", align="center", location=(0, 22))

class NoServices(Scene):
    messages = []
    text = "No services available at this time."

    def setup(self):
        self.add_text("title", align="center", font=self.board.fonts["bold"])
        self.message_element = self.add_text("message", height=36, align="center", location=(0, 14))
        self.services_element = self.add_text("noservices", text=self.text, align="center", location=(0, 22))
    
    def update_state(self, state):
        self.elements["title"].hotspot.update_text(state.name)
        self.update_messages(state.messages)
    
    def update_messages(self, messages):
        if self.messages == messages:
            return

        self.__messages = []
        self.messages = messages
        for message in messages:
            wrapped = wordwrap(self.board.fonts["regular"], 256, message)

            page = ""
            for index, line in enumerate(wrapped):
                page += line
                if (index + 1) % 3 == 0 or (index == len(wrapped) - 1):
                    # End of page
                    self.__messages.append(page)
                    page = ""
                else:
                    page += "\n"
        
        self.init_message_carousel()
    
    def init_message_carousel(self):
        if len(self.__messages) == 0:
            return
        
        self.current_message = None
        self.message_transition = datetime.now() + timedelta(seconds=Config.get("settings.messages.frequency"))
    
    def update_tick(self, timestamp, tick):
        self.update_message_carousel(timestamp)
    
    def update_message_carousel(self, timestamp):
        if len(self.messages) == 0:
            return
        
        if timestamp < self.message_transition:
            return
        
        if self.current_message == None:
            self.current_message = 0
        else:
            self.current_message += 1
        
        if self.current_message == len(self.__messages):
            self.current_message = None
            interval = Config.get("settings.messages.frequency")
            self.message_element.hide(self.board.viewport)
            self.services_element.show(self.board.viewport)
            self.services_element.hotspot.update_required = True
        
        else:
            interval = Config.get("settings.messages.interval")
            self.message_element.hotspot.update_text(self.__messages[self.current_message])
            self.services_element.hide(self.board.viewport)
            self.message_element.show(self.board.viewport)
        
        self.message_transition = timestamp + timedelta(seconds=interval)
 
class DepartureBoard(Scene):
    def setup(self):
        self.row1 = DepartureBoardRow(self, "row1", True)
        self.row3 = DepartureBoardRow(self, "row3", ypos=24)
        self.row4 = DepartureBoardRow(self, "row4", ypos=36)
        self.calling_label = self.add_text("calling_label", text="Calling at:", width=40, location=(0, 12))

        calling_at = elements.ScrollingText(214, 12, self.board.device.mode, self.board.fonts["regular"], interval=0.02, pause=80)
        self.calling_at = self.add_element("calling_at", calling_at, location=(42, 12))

    def update_state(self, state):
        final = len(state.departures) - 1
        departures = []
        for i in range(3):
            departure = None
            if i <= final:
                departure = state.departures[i]
            departures.append(departure)
        
        self.row1.update(1, departures[0])
        self.row3.update(2, departures[1])
        self.row4.update(3, departures[2])

        showtimes = Config.get("settings.layout.callingtimes", False)
        stops = []
        for stop in departures[0].stops:
            location = stop.location.get_abbr_name()
            if showtimes:
                location += " ({0})".format(stop.time)
            stops.append(location)
        
        calling_at = ""
        if stops:
            last = stops.pop()
            calling_at = ", ".join(stops)
            if calling_at:
                calling_at += " and "
            calling_at += last

        self.calling_at.hotspot.update_text(calling_at)

class DepartureBoardRow:
    order = None
    time = None
    destination = None
    platform = None
    status = None

    def __init__(self, scene, code, title=False, ypos=0):
        self.code = code
        self.scene = scene

        primary_font = self.scene.board.fonts["regular"]
        secondary_font = self.scene.board.fonts["regular"]
        if title:
            primary_font = self.scene.board.fonts["bold"]

        xoffset = 0
        destinationwidth = 176

        if Config.get("settings.layout.order", False):
            xoffset += 25
            destinationwidth -= 25
            self.order = self.scene.add_text("{0}-order".format(code), width=25, location=(0, ypos), font=primary_font)

        if Config.get("settings.layout.platform", False):
            destinationwidth -= 29
            self.platform = self.scene.add_text("{0}-platform".format(code), width=27, location=(185, ypos), font=secondary_font)
        
        self.time = self.scene.add_text("{0}-time".format(code), width=34, location=(xoffset, ypos), font=primary_font)
        self.destination = self.scene.add_text("{0}-destination".format(code), width=destinationwidth, location=(xoffset + 34, ypos), font=primary_font)
        self.status = self.scene.add_text("{0}-status".format(code), width=40, location=(216, ypos), font=secondary_font, align="right")
    
    def update(self, order, data):
        if not data:
            self.time.hotspot.update_text("")
            self.destination.hotspot.update_text("")
            self.status.hotspot.update_text("")
            if self.platform:
                self.platform.hotspot.update_text("")
            if self.order:
                self.order.hotspot.update_text("")
            return

        self.time.hotspot.update_text(data.scheduled)
        self.destination.hotspot.update_text(data.destination.get_abbr_name())
        self.status.hotspot.update_text(data.get_status_string())
        if self.platform:
            platform = ""
            if data.platform:
                platform = "Plat {0}".format(data.platform)
            self.platform.hotspot.update_text(platform)
        if self.order:
            self.order.hotspot.update_text(ordinal(order))