import trains.elements as elements
from trains.config import Config

from trains.utils import wordwrap, ordinal, get_device_id, get_ip_address

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
    
    def add_text(self, code, width=256, height=12, font=None, location=(0, 0), align="left", text="", visible=True, vertical_align="top", spacing=2):
        if not font:
            font = self.board.fonts["regular"]
        
        if code in self.elements:
            raise RuntimeError("The code has already been added")
        
        hotspot = elements.StaticText(width, height, font, self.board.device.mode, text=text, align=align, interval=0.04, vertical_align=vertical_align, spacing=spacing)
        return self.add_element(code, hotspot, location, visible)
    
    def add_scrolling_text(self, code, width=256, height=12, font=None, location=(0, 0), align="left", text="", visible=True):
        if not font:
            font = self.board.fonts["regular"]
        
        if code in self.elements:
            raise RuntimeError("The code has already been added")

        hotspot = elements.ScrollingText(width, height, font, self.board.device.mode, interval=0.04, text=text, align=align)
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
        self.add_text("initialising", text="Departure board is initialising", align="center", location=(0, 0))
        revision = "Unknown"
        with open("../REVISION") as f:
            revision = f.read()
        
        config_text = "Serial Number: {0}\n".format(get_device_id())
        config_text += "Version: {0}\n".format(revision)
        config_text += "IP Address: {0}".format(get_ip_address())
        self.add_text("config", text=config_text, height=36, location=(0, 16), spacing=4)

class NoServices(Scene):
    messages = []
    text = "No services available at this time."

    def setup(self):
        self.add_text("title", align="center", font=self.board.fonts["bold"])
        self.message_element = self.add_text("message", height=38, align="center", text=self.text, location=(0, 12), vertical_align="middle")
    
    def update_state(self, state):
        self.elements["title"].hotspot.update_text(state["name"])
        self.update_messages(state["messages"])
    
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
            self.message_element.hotspot.update_text(self.text)
        
        else:
            interval = Config.get("settings.messages.interval")
            self.message_element.hotspot.update_text(self.__messages[self.current_message])
        
        self.message_transition = timestamp + timedelta(seconds=interval)
 
class DepartureBoard(Scene):
    state = None
        
    def setup(self):
        # Next Service
        next_service = elements.NextService(self.board.fonts["regular"], self.board.device.mode)
        self.next_service = self.add_element("next_service", next_service, (0, 0)) 

        # Calling At
        self.calling_at_label = self.add_scrolling_text("calling_at_label", width=42, location=(0, 12), text="Calling at:")
        self.calling_at = self.add_scrolling_text("calling_at", width=214, location=(42, 12))

        # Info Line
        self.service_info = self.add_scrolling_text("service_info", location=(0,24))
        
        # Remaining Services
        remaining = elements.RemainingServices(self.board.fonts["regular"], self.board.device.mode)
        self.remaining = self.add_element("remaining", remaining, (0, 36))

    def update_state(self, state):
        if self.state == state:
            return
        
        self.state = state

        first = state["departures"][:1].pop()
        remaining = state["departures"][1:5]

        self.next_service.hotspot.update_data(first)

        calling_at = self.get_calling_at(first["stops"])
        self.calling_at.hotspot.update_text(calling_at)

        self.service_info.hotspot.update_text(self.get_service_info(first))
        
        self.remaining.hotspot.update_data(remaining)
    
    def get_calling_at(self, stops):
        showtimes = Config.get("settings.layout.times", False)
        stations = []
        for stop in stops:
            text = stop["location"]["abbr_name"]
            if showtimes:
                text += " ({0})".format(stop["time"])
            stations.append(text)
        
        last = stations.pop()
        calling_at = last
        if stations:
            calling_at = ", ".join(stations) + " and " + calling_at
        
        return calling_at
    
    def get_service_info(self, departure):
        info = "{0} service".format(departure["toc_name"])
        if departure["length"]:
            plural = "es"
            if departure["length"] == 1:
                plural = ""
            
            info += " formed of {0} coach{1}".format(departure["length"], plural)
        return info