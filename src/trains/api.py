import time
from datetime import datetime, timedelta
from pprint import pprint

import requests
from bs4 import BeautifulSoup

from trains.config import Config
from trains.data import *


class Api:
    __state = None
    __timestamp = None

    def get_cached_state(self, timestamp, frequency):
        if not self.__state or timestamp >= self.__timestamp:
            self.__state = self.get_state()
            self.__timestamp = timestamp + timedelta(seconds=frequency)
        return self.__state

    def get_state(self):
        departure = Config.get("settings.departure")
        url = "https://ldb.prod.a51.li/boards/{0}?term=false&t={1}000&limit=0".format(departure, int(time.time()))
        data = self.get_from_nrea(url)

        state = State()

        self.parse_station(state, data)
        self.parse_messages(state, data)
        self.parse_departures(state, data)

        return state
    
    def get_from_nrea(self, url):
        response = requests.get(url)
        return response.json()
    
    def crs_to_tiploc(self, lookup, crs):
        for station in lookup:
            if "crs" not in lookup[station]:
                continue

            if lookup[station]["crs"] == crs:
                return station
        return None

    
    def calls_at(self, lookup_data, departure, destination):
        destination_tiploc = self.crs_to_tiploc(lookup_data["tiploc"], destination)
        for station in departure["calling"]:
            if station["tpl"] == destination_tiploc:
                return True
        return False
    
    def parse_departures(self, state, data):
        destination = Config.get("settings.destination")
        platforms = Config.get("settings.platforms")
        limit = Config.get("settings.services", 3)
        if data["departures"]:
            departures = sorted(data["departures"], key=lambda departure: departure["location"]["timetable"]["time"])
        else:
            departures = []

        state.departures = []
        for departure in departures:
            if destination and not self.calls_at(data, departure, destination):
                continue

            if platforms and departure["location"]["forecast"]["plat"]["plat"] not in platforms:
                continue

            if "departed" in departure["location"]["forecast"] and departure["location"]["forecast"]["departed"]:
                continue
            
            state.departures.append(self.create_departure(data, departure))

            if len(state.departures) >= limit:
                return

    def create_departure(self, lookup_data, data):
        departure = Departure()
        
        departure.rid = data["rid"]
        departure.headcode = data["trainId"]
        departure.toc = data["toc"]
        departure.toc_name = lookup_data["toc"][data["toc"]]["tocname"]
        departure.platform = data["location"]["forecast"]["plat"]["plat"]
        if "arrived" in data["location"]["forecast"]:
            departure.arrived = data["location"]["forecast"]["arrived"]
        if "length" in data:
            departure.length = int(departure["length"])

        if departure.platform == "BUS":
            departure.bus = True

        if data["cancelReason"]["reason"] != 0:
            departure.cancelled = True
        
        departure.origin = self.get_location_from_tiploc(lookup_data, data["origin"]["tiploc"])
        departure.destination = self.get_location_from_tiploc(lookup_data, data["dest"]["tiploc"])

        departure.scheduled = data["location"]["timetable"]["time"][:5]
        departure.actual = data["location"]["forecast"]["time"][:5]
        
        departure.stops = []
        if data["calling"]:
            for calling in data["calling"]:
                stop = Stop()
                stop.location = self.get_location_from_tiploc(lookup_data, calling["tpl"])
                stop.time = calling["time"][:5]
                departure.stops.append(stop)

        return departure

    def get_location_from_tiploc(self, lookup, tiploc):
        data = lookup["tiploc"][tiploc]

        location = Location()
        location.name = data["locname"]
        location.crs = data["crs"]
        location.toc = data["toc"]
        location.toc_name = lookup["toc"][location.toc]["tocname"]

        return location
    
    def parse_station(self, state, data):
        state.location = self.get_location_from_tiploc(data, data["station"][0])
        state.name = state.location.name
    
    def parse_messages(self, state, data):
        state.messages = []
        for message in data["messages"]:
            if not state.location.crs in message["station"]:
                continue

            if "Area51" in message["message"]:
                continue

            soup = BeautifulSoup(message["message"], features="html.parser")
            text = soup.get_text()

            if not text:
                continue

            state.messages.append(text)

if __name__ == "__main__":
    state = Api().get_state()
    print(state.name)

    for departure in state.departures:
        print("\n{0} to {1} ({2}) [{3}]\n".format(departure.scheduled, departure.destination.name, departure.toc_name, departure.platform))
        for stop in departure.stops:
            print("\t[{0}] {1}".format(stop.time, stop.location.name))