#!/usr/bin/env python3
'''
Python script to get json data from Hive
python get_hive_json.py [-h] username password
'''
import requests
import json
import sys
import argparse
import os
import time

def find_key(d, value):
    for (k, v) in d.items():
        if isinstance(v, dict):
            p = find_key(v, value)
            if p:
                return [k] + p
        elif v == value:
            return [k]

def find_key_in_list(d, value):
    if isinstance(d, list):
        t = list(d)
        for v in d:
            if isinstance(v, dict):
                p = find_key(v, value)
                if not p:
                    t.remove(v)
        return t

def CreateLightPayload(State, Brightness, ColourMode = None, ColourTemperature = None, HsvSat = None):
    # state ON or OFF
    # brightness 0->100
    # colourMode COLOUR or TUNABLE : switches from colour to temperature mode
    # colourMode = COLOUR  colourTemperature(hsvHue) - 0->359, hsvSat - 0->1
    # colourMode = TUNABLE colourTemperature 2700->6535
    response = {}
    nodes = []
    attributes = {}
    state = {}
    brightness = {}
    state["targetValue"] = State
    brightness["targetValue"] = Brightness
    if ColourMode == None:
        attributes["attributes"] = {"brightness":brightness,"state":state}
    if ColourMode == "COLOUR":
        colourMode = {}
        hsvHue = {}
        hsvSat = {}
        colourMode["targetValue"] = ColourMode
        hsvHue["targetValue"] = ColourTemperature
        hsvSat["targetValue"] = HsvSat * 100
        attributes["attributes"] = {"brightness":brightness,"state":state,"colourMode":colourMode,"hsvHue":hsvHue,"hsvSaturation":hsvSat}
    if ColourMode == "TUNABLE":
        colourMode = {}
        colourTemperature = {}
        colourMode["targetValue"] = ColourMode
        colourTemperature["targetValue"] = ColourTemperature
        attributes["attributes"] = {"brightness":brightness,"state":state,"colourMode":colourMode,"colourTemperature":colourTemperature}
    nodes.append(attributes)
    response["nodes"] = nodes
    return response

parser = argparse.ArgumentParser(description='Get Hive JSON data.')
parser.add_argument('username', help='Hive Username')
parser.add_argument('password', help='Hive Password')
parser.add_argument('maxstep', type=int, default=2, nargs='?', help='max step size (default = 2)')
args = parser.parse_args()

requests.packages.urllib3.disable_warnings()

# log on to Hive
payload = {'sessions':[{'username':args.username, 'password':args.password}]}
headers = {'Content-Type': 'application/vnd.alertme.zoo-6.1+json', 'Accept': 'application/vnd.alertme.zoo-6.2+json', 'X-AlertMe-Client': 'Hive Web Dashboard'}
url = 'https://api.prod.bgchprod.info:443/omnia/auth/sessions'
r = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
sessionId = r.json()["sessions"][0]['sessionId']

headers = {'Content-Type': 'application/vnd.alertme.zoo-6.2+json', 'Accept': 'application/vnd.alertme.zoo-6.2+json', \
           'X-AlertMe-Client': 'swagger', 'X-Omnia-Access-Token': sessionId}
url = 'https://api.prod.bgchprod.info:443/omnia/nodes'
r = requests.get(url, headers=headers, verify=False)

# Find first coloured light node
nodes = r.json()["nodes"]
node = find_key_in_list(nodes, "http://alertme.com/schema/json/node.class.colour.tunable.light.json#")
DeviceID = node[0]['id']
url = 'https://api.prod.bgchprod.info:443/omnia/nodes/' + DeviceID
try:
    hsvHue = int(int.from_bytes(os.urandom(2), 'big')*359/65535)
    while True:
    #    brightness = max(1, int(int.from_bytes(os.urandom(2), 'big')*100/65535))
        brightness = 100
    #    hsvSat = int(int.from_bytes(os.urandom(1), 'big')/2.55)/100
        hsvSat = 1
        #hsvHue2 = int(int.from_bytes(os.urandom(2), 'big')*359/65535)
        hsvHue2 = int(int.from_bytes(os.urandom(2), 'big')*539/65535) # allow some red
        j = min(hsvHue,hsvHue2)
        k = max(hsvHue,hsvHue2)
        maxstep = int(args.maxstep)
        step = max(-maxstep,min(maxstep,int((hsvHue2 - hsvHue)/10)))
        if step == 0:
            step = 1
        print(str(hsvHue) + " -> " + str(hsvHue2) + " step: " + str(step))
        while j < k - abs(step) or j > k + abs(step):
            hsvHue += step
            if hsvHue < 0:
                hsvHue += 360
            #print("+++ " + str(brightness) + " " + str(hsvHue) + " " + str(hsvSat))
            payload = CreateLightPayload("ON", brightness, "COLOUR", hsvHue if hsvHue<359 else hsvHue-359, hsvSat)
            try:
                r = requests.put(url, data = json.dumps(payload).encode('ascii'), headers = headers, verify = False)
                #print(r.json())
            except Exception as e:
                print(str(e))
            j += int(abs(step))
            #print(str(j) + " " + str(k - abs(step)) + " " + str(k + abs(step)))
            time.sleep(0.1)
except KeyboardInterrupt: 
    print("Exiting")

#log out from Hive
headers = {'Content-Type': 'application/vnd.alertme.zoo-6.1+json', 'Accept': 'application/vnd.alertme.zoo-6.2+json', \
        'X-AlertMe-Client': 'Hive Web Dashboard', 'X-Omnia-Access-Token': sessionId}
url = 'https://api.prod.bgchprod.info:443/omnia/auth/sessions/' + sessionId
r = requests.delete(url, headers=headers, verify=False)

