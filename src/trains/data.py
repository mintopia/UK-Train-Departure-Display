from trains.config import Config

class Stop:
    def __init__(self):
        self.location = None
        self.time = None

class Departure:
    def __init__(self):
        self.stops = []
        self.origin = None
        self.destination = None
        self.headcode = None
        self.rid = None
        self.toc = None
        self.toc_name = None
        self.platform = None
        self.scheduled = None
        self.actual = None
        self.length = None
        self.cancelled = False
        self.bus = False
        self.arrived = False
    
    def get_status_string(self):
        if self.cancelled:
            return "Cancelled"
        elif self.arrived:
            return "Arrived"
        elif self.actual == self.scheduled:
            return "On time"
        else:
            return "Exp {0}".format(self.actual)

class Location:
    def __init__(self):
        self.name = None
        self.crs = None
        self.toc = None
        self.toc_name = None
    
    def get_abbr_name(self):
        output = self.name
        replacements = Config.get("replacements")
        if not replacements:
            return output
        for key in replacements.keys():
            output = output.replace(key, replacements[key])
        
        return output

class State:
    def __init__(self):
        self.name = None
        self.location = None
        self.departures = []
        self.messages = []
