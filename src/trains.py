import os
import requests
import json
from pprint import pprint

def abbrStation(journeyConfig, inputStr):
    dict = journeyConfig['stationAbbr']
    for key in dict.keys():
        inputStr = inputStr.replace(key, dict[key])
    return inputStr

def loadDeparturesForStation(username, password, journeyConfig):
    if journeyConfig['departureStation'] == "":
        raise ValueError(
            "Please set the journey.departureStation property in config.json")

    if username == "" or password == "":
        raise ValueError(
            "Please complete the API section of your config.json file")

    departureStation = journeyConfig['departureStation']
    destinationStation = journeyConfig['destinationStation']
    platform = journeyConfig['platform']

    URL = f"https://api.rtt.io/api/v1/json/search/{departureStation}"
    if destinationStation:
        URL += f"/to/{destinationStation}"
    
    r = requests.get(url=URL, auth=(username, password))

    data = r.json()
    #apply abbreviations / replacements to station names (long stations names dont look great on layout)
    #see config file for replacement list

    services = []
    if not data["services"]:
        return [], data["location"]["name"]

    for item in data["services"]:
        if platform and (not "platform" in item["locationDetail"] or item["locationDetail"]["platform"] != platform):
                continue
        item["locationDetail"]["origin"][0]["abbrDescription"] = abbrStation(journeyConfig, item["locationDetail"]["origin"][0]["description"])
        item["locationDetail"]["destination"][0]["abbrDescription"] = abbrStation(journeyConfig, item["locationDetail"]["destination"][0]["description"])
        services.append(item)
        if len(services) == 3:
            break

    if "error" in data:
        raise ValueError(data["error"])

    return services, data["location"]["name"]


def loadDestinationsForDeparture(username, password, journeyConfig, serviceData):
    uid = serviceData["serviceUid"]
    date = serviceData["runDate"].replace("-", "/")
    url = f"https://api.rtt.io/api/v1/json/service/{uid}/{date}"
    r = requests.get(url=url, auth=(username, password))

    data = r.json()

    #apply abbreviations / replacements to station names (long stations names dont look great on layout)
    #see config file for replacement list
    foundDepartureStation = False

    for item in list(data["locations"]):
        if item['crs'] == journeyConfig['departureStation']:
            foundDepartureStation = True

        if foundDepartureStation == False:
            data["locations"].remove(item)
            continue

        item["abbrDescription"] = abbrStation(journeyConfig, item["description"])

    if "error" in data:
        raise ValueError(data["error"])

    departureDestinationList = list(map(lambda x: x["abbrDescription"], data["locations"]))[1:]

    if len(departureDestinationList) == 1:
        departureDestinationList[0] = departureDestinationList[0] + ' only.'

    return departureDestinationList
