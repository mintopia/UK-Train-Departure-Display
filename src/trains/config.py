import json
import pprint
import os

class Config:
    instance = None

    def __init__(self):
        filename = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                '../'
                'config.json'
            )
        )
        print("Reading config from {0}".format(filename))
        with open(filename, 'r') as jsonConfig:
            self.config = json.load(jsonConfig)
    
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