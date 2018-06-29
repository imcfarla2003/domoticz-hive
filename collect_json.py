#!/usr/bin/env python
'''
Python script to get json data from Hive
python get_hive_json.py [-h] username password
'''
import requests
import json
import sys
import argparse

parser = argparse.ArgumentParser(description='Get Hive JSON data.')
parser.add_argument('username', help='Hive Username')
parser.add_argument('password', help='Hive Password')
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

# Find thermostat node
print(r.json()["nodes"])

# log out from Hive
headers = {'Content-Type': 'application/vnd.alertme.zoo-6.1+json', 'Accept': 'application/vnd.alertme.zoo-6.2+json', \
        'X-AlertMe-Client': 'Hive Web Dashboard', 'X-Omnia-Access-Token': sessionId}
url = 'https://api.prod.bgchprod.info:443/omnia/auth/sessions/' + sessionId
r = requests.delete(url, headers=headers, verify=False)

