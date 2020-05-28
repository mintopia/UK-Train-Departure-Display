import json
import pprint
import os
import requests

class Config:
    instance = None

    def __init__(self):
        uuid = os.environ['BALENA_DEVICE_UUID']
        url = "http://192.168.30.187/config/{0}".format(uuid[:7])
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