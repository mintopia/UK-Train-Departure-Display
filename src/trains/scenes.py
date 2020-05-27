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
    
    def add_messagebar(self, code, width=256, height=12, font=None, location=(0, 0), align="left", messages=[], visible=True, hold_time=4, minimum_time=20):
        if not font:
            font = self.board.fonts["regular"]
        
        if code in self.elements:
            raise RuntimeError("The code has already been added")

        hotspot = elements.MessageBar(width, height, font, self.board.device.mode, interval=0.02, messages=messages, hold_time=hold_time, minimum_time=minimum_time, align=align)
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
        self.row4 = DepartureBoardRow(self, "row4", ypos=36)
        self.calling_label = self.add_messagebar("calling_label", messages=["Calling at:"], width=40, location=(0, 12))
        self.calling_at = self.add_messagebar("calling_at", width=214, location=(42, 12), hold_time=3)
        self.messages = self.add_messagebar("message", location=(0, 24), minimum_time=10)

        self.calling_at.hotspot.debug = True
        self.calling_at.hotspot.next_image.debug = True
        self.calling_at.hotspot.current_image.debug = True

    def update_state(self, state):
        self.row1.update(1, state.departures[0:1])
        self.row4.update(2, state.departures[1:4])

        first = state.departures[0]

        service = "{0} service".format(first.toc_name)
        if first.length:
            service += " formed of {0} coach".format(first.length)
            if first.length != 1:
                service += "es"
        messages = [
            service
        ]
        self.messages.hotspot.update_messages(messages)

        showtimes = Config.get("settings.layout.callingtimes", False)
        stops = []
        for stop in first.stops:
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

        self.calling_at.hotspot.update_messages([calling_at])

class DepartureBoardRow:
    order = None
    time = None
    destination = None
    platform = None
    status = None

    def __init__(self, scene, code, title=False, ypos=0):
        self.code = code
        self.scene = scene
        self.data = None

        font = self.scene.board.fonts["regular"]
        minimum_time = 10

        self.order = self.scene.add_messagebar("{0}-order".format(code), width=20, location=(0, ypos), minimum_time=minimum_time)
        self.time = self.scene.add_messagebar("{0}-time".format(code), width=28, location=(20, ypos), align="center", minimum_time=minimum_time)
        self.platform = self.scene.add_messagebar("{0}-platform".format(code), width=16, location=(48, ypos), align="center", minimum_time=minimum_time)
        
        self.destination = self.scene.add_messagebar("{0}-destination".format(code), width=149, location=(67, ypos), minimum_time=minimum_time)
        self.status = self.scene.add_messagebar("{0}-status".format(code), width=40, location=(216, ypos),align="right", minimum_time=minimum_time)
    
    def update(self, starting_order, data):
        if data == self.data:
            return
        
        if not data:
            self.time.hotspot.update_messages()
            self.destination.hotspot.update_messages()
            self.status.hotspot.update_messages()
            self.platform.hotspot.update_messages()
            self.order.hotspot.update_messages()
            return

        order = []
        scheduled = []
        platform = []
        destination = []
        status = []
        
        for departure in data:
            order.append(ordinal(starting_order))
            scheduled.append(departure.scheduled)
            platform.append(departure.platform)
            destination.append(departure.destination.get_abbr_name())
            status.append(departure.get_status_string())

            starting_order += 1

        self.order.hotspot.update_messages(order)
        self.time.hotspot.update_messages(scheduled)
        self.platform.hotspot.update_messages(platform)
        self.destination.hotspot.update_messages(destination)
        self.status.hotspot.update_messages(status)