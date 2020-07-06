import json
import pprint
import os
import requests

from trains.utils import get_device_id

class Config:
    instance = None
    __id = None

    def __init__(self):
        uid = get_device_id()
        url = "https://orion.42m.co.uk/trains/config/{0}.json".format(uid)
        response = requests.get(url)
        self.config = response.json()
    
    def lookup(self, path):
        keys = path.split(".")
        return self.__lookup(keys, self.config)
    
    def __lookup(self, keys, config):
        if len(keys) == 0:
            return None
        key = keys.pop(0)
        if key in config:
            if type(config[key]) is dict:
                return self.__lookup(keys, config[key])
            
            return config[key]
        return None


    @staticmethod
    def get(path, default=None):
        if not Config.instance:
            Config.instance = Config()
        
        result = Config.instance.lookup(path)
        if result == None:
            return default
        return result

if __name__ == "__main__":
    print("Departure: {0}".format(Config.get("settings.departure")))