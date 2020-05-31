import json
import pprint
import os
import requests

from getmac import get_mac_address

class Config:
    instance = None
    __id = None

    def __init__(self):
        uid = self.get_device_id()
        url = "http://192.168.30.187/config/{0}.json".format(uid)
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
        
    
    def get_device_id(self):
        if self.__id:
            return self.__id
        
        # We need a unique device ID for config, etc. Let's use MAC address.
        mac = get_mac_address()
        
        self.__id = mac.replace(":", "")
        return self.__id


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