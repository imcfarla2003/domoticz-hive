'''
<plugin key="HivePlug" name="Hive Plugin" author="imcfarla, MikeF and roadsnail" version="1.0-urllib" wikilink="http://www.domoticz.com/wiki/plugins" externallink="https://github.com/imcfarla2003/domoticz-hive">
    <description>
        <h2>Hive Plugin</h2>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Thermostats (including multizone)</li>
            <li>Active lights</li>
            <li>Warm to Cool lights</li>
            <li>Colour lights</li>
            <li>Activeplugs</li>
        </ul>
        <h3>To Do</h3>
        <ul style="list-style-type:square">
            <li>Allow to choose the heating mode from boost, scheduled, manual and off</li>
        </ul>
    </description>
    <params>
        <param field="Username" label="Hive Username" width="200px" required="true" default=""/>
        <param field="Password" label="Hive Password" width="200px" required="true" default=""/>
        <param field="Mode1" label="Heartbeat Multiplier" width="30px" required="true" default="1"/>
        <param field="Mode2" label="Domoticz Port - only needed prior to version 3.8791" width="40px" required="false" default="8080"/>
        <param field="Mode3" label="Postcode" width="100px" required="false" default=""/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
'''
try:
    import json
    import math
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
    from urllib.error import HTTPError
    import Domoticz
except ImportError as L_err:
    print("ImportError: {0}".format(L_err))
    raise L_err

class BasePlugin:
    enabled = False
    
    def __init__(self):
        self.sessionId = ''
        self.counter = 0
        self.multiplier = 10
        self.lightsSet = set()
        self.activeplugsSet = set()
        self.hwrelaySet = set()
        self.chrelaySet = set()
        self.TimedOutAvailable = False
    
    def onStart(self):
        Domoticz.Log('Starting')
        if Parameters["Mode6"] != "0":
            if Parameters["Mode6"] == "Normal":
                Domoticz.Debugging(0)
            elif Parameters["Mode6"] == "null":
                Domoticz.Debugging(0)
            elif Parameters["Mode6"] == "Debug":
                Domoticz.Debugging(-1)
            else:
                Domoticz.Debugging(int(Parameters["Mode6"]))
        if int(self.getDomoticzRevision()) >= 8651: 
            # Devices[unit].TimedOut only appears in Revision >= 8651
            self.TimedOutAvailable = True
            Domoticz.Log("TimedOut available")
        else:
            Domoticz.Log("TimedOut not available: " + self.getDomoticzRevision())
        self.multiplier = int(Parameters['Mode1'])
        self.counter = self.multiplier # update immediately
        if self.sessionId == '':
            Domoticz.Log('Creating Session')
            self.GetSessionID()
        Domoticz.Debug(self.sessionId)
        self.onHeartbeat()

    def onStop(self):
        Domoticz.Log('Deleting Session')
        headers = {'Content-Type': 'application/vnd.alertme.zoo-6.1+json', 
                   'Accept': 'application/vnd.alertme.zoo-6.2+json', 
                   'X-AlertMe-Client': 'Hive Web Dashboard', 
                   'X-Omnia-Access-Token': self.sessionId }
        url = 'https://api.prod.bgchprod.info:443/omnia/auth/sessions/' + self.sessionId
        req = Request(url, headers = headers)
        req.get_method = lambda : 'DELETE'
        try:
            r = urlopen(req).read()
        except Exception as e:
            Domoticz.Log(str(e))
    
    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug('onConnect called')
    
    def onMessage(self, Connection, Data):
        Domoticz.Debug('onMessage called')
    
    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log('onCommand called for Unit ' + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        Domoticz.Debug(str(Devices[Unit].Type))
        Domoticz.Debug(str(Devices[Unit].SubType))
        Domoticz.Debug(Devices[Unit].DeviceID)
        Domoticz.Debug(str(Devices[Unit].sValue))
        payload = ""
        if self.isLight(Unit):
            Domoticz.Log("Setting Light Parameters")
            if str(Command) == "Set Level":
                payload = self.CreateLightPayload("ON", Level)
            if str(Command) == "On":
                payload = self.CreateLightPayload("ON", Devices[Unit].LastLevel)
            if str(Command) == "Off":
                payload = self.CreateLightPayload("OFF", Devices[Unit].LastLevel)
            if str(Command) == "Set Color":
                Domoticz.Debug(Hue)
                colourDict = json.loads(Hue)
                colourMode = colourDict.get("m")
                if colourMode == 2:
                    # white temp
                    colourTemp = 6533-(colourDict.get("t")*15)
                    Domoticz.Debug(str(colourTemp))
                    payload = self.CreateLightPayload("ON", Level, "TUNABLE", colourTemp)
                elif colourMode == 3:
                    # rgb colour
                    h, s, v = rgb2hsv(colourDict.get("r"),colourDict.get("g"),colourDict.get("b"))
                    Domoticz.Debug(str(h) + " " + str(s) + " " +str(v))
                    payload = self.CreateLightPayload("ON", Level, "COLOUR", h, s)
                else:
                   Domoticz.Log("Colour Mode not supported: " + str(colourMode))
        elif self.isThermostat(Unit):
            Domoticz.Log("Setting Thermostat Level")
            payload = self.CreateThermostatPayload(Level)
        elif self.isActivePlug(Unit):
            Domoticz.Log("Setting ActivePlug State")
            if str(Command) == "On":
                payload = self.CreateActivePlugPayload("ON")
            if str (Command) == "Off":
                payload = self.CreateActivePlugPayload("OFF")
        elif self.isHotWaterRelay(Unit):
            Domoticz.Log("Setting Hot Water Relay State")
            if str(Command) == "On":
                payload = self.CreateHotWaterPayload("HEAT") # Android APP Shows as On
            if str(Command) == "Off":
                payload = self.CreateHotWaterPayload("OFF") # Android APP shows as Off
        elif self.isCentralHeatingRelay(Unit):
            Domoticz.Log("Setting Central Heating Relay State")
            if str(Command) == "On":
                payload = self.CreateCentralHeatingPayload("HEAT") # Android APP Shows as Manual (Governed by Thermostat setting)
            if str(Command) == "Off":
                payload = self.CreateCentralHeatingPayload("OFF") # Android APP shows as Off
        else:
            Domoticz.Log("Unknown Device Type")
        if payload != "":
            headers = {'Content-Type': 'application/vnd.alertme.zoo-6.2+json', 
                       'Accept': 'application/vnd.alertme.zoo-6.2+json', 
                       'X-AlertMe-Client': 'swagger', 
                       'X-Omnia-Access-Token': self.sessionId}
            url = 'https://api.prod.bgchprod.info:443/omnia/nodes/' + Devices[Unit].DeviceID
            req = Request(url, data = json.dumps(payload).encode('ascii'), headers = headers, unverifiable = True)
            req.get_method = lambda : 'PUT'
            try:
                r = urlopen(req).read().decode('utf-8')
                # Process the update sent back from Hive
                d = json.loads(r)['nodes']
                self.UpdateDeviceState(d)
            except Exception as e:
                Domoticz.Log(str(e))
        else:
            Domoticz.Log(str(Command) + " not handled")
    
    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug('Notification: ' + Name + ',' + Subject + ',' + Text + ',' + Status + ',' + str(Priority) + ',' + Sound + ',' + ImageFile)
    
    def onDisconnect(self, Connection):
        Domoticz.Debug('onDisconnect called')
    
    def onHeartbeat(self):
        Domoticz.Debug('onHeartbeat called')
        if self.counter >= self.multiplier:
            Domoticz.Debug('Getting Data')
            self.counter = 1
            d = self.GetDevices()
            self.UpdateDeviceState(d)
            if Parameters["Mode3"] != "":   #if postcode parameter set for Hive outside temp then....
                foundOutsideDevice = False
                w = self.GetWeatherURL()
                if w != False:
                    outsidetemp = w["temperature"]["value"]
    
                    for unit in Devices:
                        if Devices[unit].DeviceID == "Hive_Outside":
                            Devices[unit].Update(nValue=int(outsidetemp), sValue=str(outsidetemp))
                            foundOutsideDevice = True
    
                    if foundOutsideDevice == False:
                        Domoticz.Device(Name = 'Outside', 
                                        Unit = self.GetNextUnit(False), 
                                        TypeName = 'Temperature', 
                                        DeviceID = 'Hive_Outside').Create()
                        self.counter = self.multiplier

        else:
            self.counter += 1
            Domoticz.Debug('Counter = ' + str(self.counter))

    def GetThermostat(self, d, ttype):
        #ttype can be 'Heating' or 'HotWater'
        thermostats = False
        k = 'state'+ttype+'Relay'
        x = find_key_in_list(d, 'http://alertme.com/schema/json/node.class.thermostat.json#')
        if x:
            for i in x:
                if k in i['attributes']:
                    if thermostats:
                        thermostats.append(i)
                    else:
                        thermostats = [i]
        return thermostats

    def GetThermostatUI(self, d, parentNodeId):
        thermostatui = False
        x = find_key_in_list(d, 'http://alertme.com/schema/json/node.class.thermostatui.json#')
        if not x: # Try a Hive2 thermostat
            x = find_key_in_list(d,"Hive2")
        if x:
            for i in x:
                try:
                    if i["relationships"]["boundNodes"][0]["id"] == parentNodeId:
                        thermostatui = i
                except Exception as e:
                    Domoticz.Debug("Thermostatui - No boundNodes under relationship")
        if len(x) == 1:
            Domoticz.Debug("Only one thermostatui node so using that")
            thermostatui = x[0]
        return thermostatui

    def GetLights(self, d):
        lights = False
        x = find_key_in_list(d,"http://alertme.com/schema/json/node.class.light.json#")
        if x:
            lights = x
        return lights

    def GetTunableLights(self, d):
        lights = False
        x = find_key_in_list(d,"http://alertme.com/schema/json/node.class.tunable.light.json#")
        if x:
            lights = x
        return lights

    def GetColourLights(self, d):
        lights = False
        x = find_key_in_list(d,"http://alertme.com/schema/json/node.class.colour.tunable.light.json#")
        if x:
            lights = x
        return lights

    def GetActivePlugs(self, d):
        activeplugs = False
        x = find_key_in_list(d,"http://alertme.com/schema/json/node.class.smartplug.json#")
        if x:
            activeplugs = x
        return activeplugs

    def GetNextUnit(self, unit):
        if not unit:
            nextUnit = len(Devices) + 1
        else:
            nextUnit = unit +1
        if nextUnit in Devices or nextUnit < 1:
            nextUnit = self.GetNextUnit(nextUnit)
        Domoticz.Log("Unit " + str(nextUnit))
        return nextUnit

    def UpdateDeviceState(self, d):
        foundHotWaterDevice = False
        foundOutsideDevice = False

        Domoticz.Debug('Getting Temperatures')
        thermostats = self.GetThermostat(d, 'Heating')
        if thermostats:
            for node in thermostats:
                # TODO: add schedule switch to change toggle scheduled or off (chrelay switch toggles manual or off)
                # TODO: add switch for boost mode (fix time to half an hour)
                foundInsideDevice = False
                foundTargetDevice = False
                foundHeatingDevice = False
                foundThermostatDevice = False
                # get the temperature and heating states
                temp = node["attributes"]["temperature"]["reportedValue"]
                Domoticz.Debug('Temp = ' + str(temp))
                targetTemp = node["attributes"]["targetHeatTemperature"]["reportedValue"]
                if targetTemp < 7.0: targetTemp = 7.0
                Domoticz.Debug('Target = ' + str(targetTemp))
                heating = node["attributes"]["stateHeatingRelay"]["reportedValue"]
                Domoticz.Debug('Heating = ' + heating)
                Domoticz.Debug('Getting Battery Status')
                thermostatui = self.GetThermostatUI(d, node["parentNodeId"])
                if (thermostatui):
                    # get the battery and rssi values
                    thermostat_battery = thermostatui["attributes"]["batteryLevel"]["reportedValue"]
                    Domoticz.Debug('Battery = ' + str(thermostat_battery))
                    thermostat_rssi = 12*((0 - thermostatui["attributes"]["RSSI"]["reportedValue"])/100)
                    Domoticz.Debug('RSSI = ' + str(thermostat_rssi))

                # Loop through the devices and update temperatures
                Domoticz.Debug('Updating Devices')
                for unit in Devices:
                    if Devices[unit].DeviceID == node["name"]+"_Current":
                        Devices[unit].Update(nValue=int(temp), sValue=str(temp))
                        foundInsideDevice = True
                    if Devices[unit].DeviceID == node["name"]+"_Target":
                        Devices[unit].Update(nValue=int(targetTemp), sValue=str(targetTemp))
                        foundTargetDevice = True
                    if Devices[unit].DeviceID == node["id"] and Devices[unit].Type == 244:	#if CH Switch device
                        foundHeatingDevice = True
                        if unit not in set(self.chrelaySet):
                            self.chrelaySet.add(unit)
                        if (thermostatui):
                                if thermostatui["attributes"]["presence"]["reportedValue"] == "ABSENT":
                                    if self.TimedOutAvailable:
                                        if Devices[unit].TimedOut == 0:
                                            Devices[unit].Update(nValue=Devices[unit].nValue, sValue=Devices[unit].sValue, TimedOut=1)
                                    else:
                                        Domoticz.Log("Device Offline : " + Devices[unit].Name)
                                else:
                                    if heating == 'ON':
                                        if Devices[unit].nValue == 0:
                                            if self.TimedOutAvailable:
                                                Devices[unit].Update(nValue=1, sValue='On', TimedOut=0)
                                            else:
                                                Devices[unit].Update(nValue=1, sValue='On')
                                    else:
                                        if Devices[unit].nValue == 1:
                                            if self.TimedOutAvailable:
                                                Devices[unit].Update(nValue=0, sValue='Off', TimedOut=0)
                                            else:
                                                Devices[unit].Update(nValue=0, sValue='Off')
                    if Devices[unit].DeviceID == node['id'] and Devices[unit].Type == 242: #Thermostat
                        foundThermostatDevice = True
                        Devices[unit].Update(nValue = int(targetTemp),
                                             sValue = str(targetTemp),
                                             BatteryLevel = int(thermostat_battery),
                                             SignalLevel = int(thermostat_rssi))
                if foundInsideDevice == False and thermostatui:
                    Domoticz.Device(Name = thermostatui["name"] + ' - Current',
                                    Unit = self.GetNextUnit(False),
                                    TypeName = 'Temperature',
                                    DeviceID = node["name"]+'_Current').Create()
                    self.counter = self.multiplier
                if foundTargetDevice == False and thermostatui:
                    Domoticz.Device(Name = thermostatui["name"] + ' - Target',
                                    Unit = self.GetNextUnit(False),
                                    TypeName = 'Temperature',
                                    DeviceID = node["name"]+'_Target').Create()
                    self.counter = self.multiplier
                if foundHeatingDevice == False and thermostatui:
                    Domoticz.Device(Name = thermostatui["name"] + ' - Heating',
                                    Unit = self.GetNextUnit(False),
                                    TypeName = 'Switch',
                                    Switchtype = 0,
                                    DeviceID = node['id']).Create()
                    self.counter = self.multiplier
                if foundThermostatDevice == False and thermostatui:
                    Domoticz.Device(Name = thermostatui["name"] + ' - Thermostat',
                                    Unit = self.GetNextUnit(False),
                                    Type = 242,
                                    Subtype = 1,
                                    DeviceID = node['id']).Create()
                    self.counter = self.multiplier
        else:
            Domoticz.Debug('No heating thermostat found')

        thermostatsW = self.GetThermostat(d, 'HotWater')
        if thermostatsW: # HotWater too...
            thermostatW = thermostatsW[0]
            hotwater = thermostatW["attributes"]["stateHotWaterRelay"]["reportedValue"]
            for unit in Devices:
                if Devices[unit].DeviceID == thermostatW["id"]:
                    foundHotWaterDevice = True
                    if unit not in set(self.hwrelaySet):
                        self.hwrelaySet.add(unit)
                    if (thermostatui):
                            if thermostatui["attributes"]["presence"]["reportedValue"] == "ABSENT":
                                if self.TimedOutAvailable:
                                    if Devices[unit].TimedOut == 0:
                                        Devices[unit].Update(nValue=Devices[unit].nValue, sValue=Devices[unit].sValue, TimedOut=1)
                                else:
                                    Domoticz.Log("Device Offline : " + Devices[unit].Name)
                            else:
                                if hotwater == 'ON':
                                    if Devices[unit].nValue == 0:
                                        if self.TimedOutAvailable:
                                            Devices[unit].Update(nValue=1, sValue='On', TimedOut=0)
                                        else:
                                            Devices[unit].Update(nValue=1, sValue='On')
                                else:
                                    if Devices[unit].nValue == 1:
                                        if self.TimedOutAvailable:
                                            Devices[unit].Update(nValue=0, sValue='Off', TimedOut=0)
                                        else:
                                            Devices[unit].Update(nValue=0, sValue='Off')
            if foundHotWaterDevice == False:
                Domoticz.Device(Name = 'HotWater - Relay',
                                Unit = self.GetNextUnit(False),
                                TypeName = 'Switch',
                                Switchtype = 0,
                                DeviceID = thermostatW["id"]).Create()
                self.counter = self.multiplier
        else:
             Domoticz.Debug('No hot water thermostat/relay found')

        lights = self.GetLights(d)
        tunablelights = self.GetTunableLights(d)
        colourlights = self.GetColourLights(d)
        if lights:
            Domoticz.Debug("Found Standard Light(s)")
            if colourlights:
                Domoticz.Debug("Found Colour Light(s)")
                lights += colourlights
                if tunablelights:
                    Domoticz.Debug("Found Tunable Light(s)")
                    lights += tunablelights
            else:
                if tunablelights:
                    Domoticz.Debug("Found Tunable Light(s)")
                    lights += tunablelights
        else:
            if colourlights:
                Domoticz.Debug("Found Colour Light(s)")
                lights = colourlights
                if tunablelights:
                    Domoticz.Debug("Found Tunable Light(s)")
                    lights += tunablelights
            else:
                if tunablelights:
                    Domoticz.Debug("Found Tunable Light(s)")
                    lights = tunablelights
        if lights:
            for node in lights:
                Domoticz.Debug("Light detected " + node["name"])
                if "RSSI" in node["attributes"]:
                    rssi = 12*((0 - node["attributes"]["RSSI"]["reportedValue"])/100)
                else:
                    rssi = 0
                found = False
                for unit in Devices:
                    if node['id'] == Devices[unit].DeviceID:
                        if unit not in set(self.lightsSet):
                            self.lightsSet.add(unit)
                        Domoticz.Debug(Devices[unit].Name + ": " + node["attributes"]["presence"]["reportedValue"])
                        if node["attributes"]["presence"]["reportedValue"] == "ABSENT":
                            if self.TimedOutAvailable:
                                if Devices[unit].TimedOut == 0:
                                    Devices[unit].Update(nValue=0, sValue='Off', TimedOut=1, SignalLevel=0)
                            else:
                                Domoticz.Log("Device Offline : " + Devices[unit].Name)
                        else:
                            # Work on targetValues (allows to update devices on the return of an update posted but not yet executed)
                            if "targetValue" not in node["attributes"]["state"]:
                                node["attributes"]["state"]["targetValue"] == node["attributes"]["state"]["reportedValue"]
                            Domoticz.Debug("State: " + Devices[unit].sValue + " -> " + node["attributes"]["state"]["targetValue"])
                            if node["attributes"]["state"]["targetValue"] == "OFF":
                                if Devices[unit].nValue != 0: # Device not already off
                                    if self.TimedOutAvailable:
                                        Devices[unit].Update(nValue=0, sValue='Off', TimedOut=0, SignalLevel=int(rssi))
                                    else:
                                        Devices[unit].Update(nValue=0, sValue='Off', SignalLevel=int(rssi))
                                else: # Device is already off but could have been timed out
                                    if self.TimedOutAvailable:
                                        if Devices[unit].TimedOut:
                                            Devices[unit].Update(nValue=0, sValue='Off', TimedOut=0, SignalLevel=int(rssi))
                            else:
                                Domoticz.Debug("Brightness Target: " + str(Devices[unit].LastLevel))
                                Domoticz.Debug("Brightness: " + str(node["attributes"]["brightness"]["targetValue"]))
                                if Devices[unit].LastLevel != int(node["attributes"]["brightness"]["targetValue"]) or Devices[unit].sValue == 'Off':
                                    if self.TimedOutAvailable:
                                        if node["attributes"]["model"]["reportedValue"] == "RGBBulb01UK":
                                            # Don't bother with colours as there is currently nowhere in domoticz to store these
                                            # 1 = Set Level for rgbww dimmer
                                            Devices[unit].Update(nValue=1,
                                                                 sValue=str(node["attributes"]["brightness"]["targetValue"]),
                                                                 TimedOut=0,
                                                                 SignalLevel=int(rssi))
                                        elif node["attributes"]["model"]["reportedValue"] == "TWBulb01UK" \
                                            or node["attributes"]["model"]["reportedValue"] == "TWBulb01US" \
                                            or node["attributes"]["model"]["reportedValue"] == "TWGU10Bulb01UK":
                                            # 1 = Set Level for ww dimmer
                                            Devices[unit].Update(nValue=1,
                                                                 sValue=str(node["attributes"]["brightness"]["targetValue"]),
                                                                 TimedOut=0,
                                                                 SignalLevel=int(rssi))
                                        elif node["attributes"]["model"]["reportedValue"] == "FWBulb01" \
                                            or node["attributes"]["model"]["reportedValue"] == "FWBulb02UK" \
                                            or node["attributes"]["model"]["reportedValue"] == "FWCLBulb01":
                                            # 2 = Set Level
                                            Devices[unit].Update(nValue=2,
                                                                 sValue=str(node["attributes"]["brightness"]["targetValue"]),
                                                                 TimedOut=0,
                                                                 SignalLevel=int(rssi))
                                        else:
                                            Domoticz.Debug("Unknown Light")
                                    else:
                                        # 2 = Set Level
                                        Devices[unit].Update(nValue=2,
                                                             sValue=str(node["attributes"]["brightness"]["targetValue"]),
                                                             SignalLevel=int(rssi))
                        found = True
                        Domoticz.Debug("Light finished " + node["name"])
                        break
                if not found:
                    Domoticz.Log("Light not found " + node["name"])
                    created = False
                    newUnit = self.GetNextUnit(False)
                    if node["attributes"]["model"]["reportedValue"] == "RGBBulb01UK":
                        # RGB WW CW Bulb
                        Domoticz.Device(Name = node["name"],
                                        Unit = newUnit,
                                        Type=241,
                                        Subtype=4,
                                        Switchtype=7,
                                        DeviceID = node['id']).Create()
                        created = True
                    elif node["attributes"]["model"]["reportedValue"] == "TWBulb01UK" \
                        or node["attributes"]["model"]["reportedValue"] == "TWBulb01US" \
                        or node["attributes"]["model"]["reportedValue"] == "TWGU10Bulb01UK":
                        # TW CW Bulb
                        Domoticz.Device(Name = node["name"],
                                        Unit = newUnit,
                                        Type=241,
                                        Subtype=8,
                                        Switchtype=7,
                                        DeviceID = node['id']).Create()
                        created = True
                    elif node["attributes"]["model"]["reportedValue"] == "FWBulb01" \
                        or node["attributes"]["model"]["reportedValue"] == "FWBulb02UK" \
                        or node["attributes"]["model"]["reportedValue"] == "FWCLBulb01":
                        # Standard dimmable light
                        Domoticz.Device(Name = node["name"],
                                        Unit = newUnit,
                                        Type=244,
                                        Subtype=73,
                                        Switchtype=7,
                                        DeviceID = node['id']).Create()
                        created = True
                    else:
                        Domoticz.Debug("Unknown Light")
                    if created:
                        if "state" in node["attributes"]:
                            if node["attributes"]["state"]["reportedValue"] == "OFF":
                                Domoticz.Debug("New Device Off")
                                Devices[newUnit].Update(nValue=0, sValue='Off', SignalLevel=int(rssi))
                            else:
                                Domoticz.Debug("New Device On")
                                Devices[newUnit].Update(nValue=2,
                                                        sValue=str(node["attributes"]["brightness"]["reportedValue"]),
                                                        SignalLevel=int(rssi)) # 2 = Set Level
                        else:
                            Devices[newUnit].Update(nValue=0, sValue='Off', SignalLevel=int(rssi))

        activeplugs = self.GetActivePlugs(d)
        if activeplugs:
            for node in activeplugs:
                for unit in Devices:
                    # Active plugs also have internalTemperature, energyConsumed and powerConsumption
                    if "RSSI" in node["attributes"]:
                        rssi = 12*((0 - node["attributes"]["RSSI"]["reportedValue"])/100)
                    else:
                        rssi = 0
                    if node['id'] == Devices[unit].DeviceID and Devices[unit].Type == 244:
                        if unit not in set(self.activeplugsSet):
                            self.activeplugsSet.add(unit)
                        if node["attributes"]["presence"]["reportedValue"] == "ABSENT":
                            if self.TimedOutAvailable:
                                if Devices[unit].TimedOut == 0:
                                    Devices[unit].Update(nValue=Devices[unit].nValue,
                                                         sValue=Devices[unit].sValue,
                                                         TimedOut=1,
                                                         SignalLevel=0)
                            else:
                                Domoticz.Log("Device Offline : " + Devices[unit].Name)
                        else:
                            if node["attributes"]["state"]["reportedValue"] == "OFF":
                                if Devices[unit].nValue != 0:
                                    if self.TimedOutAvailable:
                                        Devices[unit].Update(nValue=0, sValue='Off', TimedOut=0, SignalLevel=int(rssi))
                                    else:
                                        Devices[unit].Update(nValue=0, sValue='Off', SignalLevel=int(rssi))
                            else:
                                Domoticz.Debug("State: " + Devices[unit].sValue)
                                if Devices[unit].nValue != 1:
                                    if self.TimedOutAvailable:
                                        Devices[unit].Update(nValue=1, sValue='On', TimedOut=0, SignalLevel=int(rssi))
                                    else:
                                        Devices[unit].Update(nValue=1, sValue='On', SignalLevel=int(rssi))
                        for unit1 in Devices:
                            if node['id'] == Devices[unit1].DeviceID and Devices[unit1].Type == 80:
                                if "internalTemperature" in node["attributes"]:
                                    Domoticz.Debug("ActivePlug Temperature found " + node["name"])
                                    Devices[unit1].Update(nValue = 0, sValue = str(node["attributes"]["internalTemperature"]["reportedValue"]))
                                break
                        else:
                            # Create a temperature device to go with the plug
                            Domoticz.Debug("ActivePlug Temperature not found " + node["name"])
                            newUnit = self.GetNextUnit(False)
                            Domoticz.Device(Name = node["name"]+" - Temperature",
                                            Unit = newUnit,
                                            TypeName = "Temperature",
                                            DeviceID = node['id']).Create()
                            Devices[newUnit].Update(nValue = 0, sValue = str(node["attributes"]["internalTemperature"]["reportedValue"]))
                        break
                else:
                    Domoticz.Log("ActivePlug not found " + node["name"])
                    newUnit = self.GetNextUnit(False)
                    Domoticz.Device(Name = node["name"],
                                    Unit = newUnit,
                                    TypeName = "Switch",
                                    Switchtype = 0,
                                    DeviceID = node['id']).Create()
                    if "state" in node["attributes"]:
                        if node["attributes"]["state"]["reportedValue"] == "OFF":
                            Devices[newUnit].Update(nValue=0, sValue='Off', SignalLevel=int(rssi))
                        else:
                            Devices[unit].Update(nValue=1, sValue='On', SignalLevel=int(rssi))
                    else:
                        Devices[newUnit].Update(nValue=0, sValue='Off', SignalLevel=int(rssi))
                    # Create a temperature device to go with the plug
                    newUnit = self.GetNextUnit(False)
                    Domoticz.Device(Name = node["name"]+" - Temperature",
                                    Unit = newUnit,
                                    TypeName = "Temperature",
                                    DeviceID = node['id']).Create()
                    if "internalTemperature" in node["attributes"]:
                        Devices[newUnit].Update(nValue = 0, sValue = str(node["attributes"]["internalTemperature"]["reportedValue"]))
                    else:
                        Devices[newUnit].Update(nValue = 0, sValue = "0")

    def CreateLightPayload(self, State, Brightness, ColourMode = None, ColourTemperature = None, HsvSat = None):
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

    def CreateThermostatPayload(self, Temperature):
        response = {}
        nodes = []
        attributes = {}
        targetHeatTemperature = {}
        targetHeatTemperature["targetValue"] = Temperature
        attributes["attributes"] = {"targetHeatTemperature":targetHeatTemperature}
        nodes.append(attributes)
        response["nodes"] = nodes
        return response

    def CreateActivePlugPayload(self, State):
        response = {}
        nodes = []
        attributes = {}
        state = {}
        state["targetValue"] = State
        attributes["attributes"] = {"state":state}
        nodes.append(attributes)
        response["nodes"] = nodes
        return response

    def CreateHotWaterPayload(self, State):
        response = {}
        nodes = []
        attributes = {}
        if State == "HEAT":
            Domoticz.Debug('HW On')
            attributes["attributes"] = {"activeHeatCoolMode": {"targetValue": "HEAT"},"activeScheduleLock": {"targetValue": "True"}}
        if State == "OFF":
            Domoticz.Debug('HW Off')
            attributes["attributes"] = {"activeHeatCoolMode": {"targetValue": "OFF"},"activeScheduleLock": {"targetValue": "False"}}
        nodes.append(attributes)
        response["nodes"] = nodes
        return response

    def CreateCentralHeatingPayload(self, State):
        response = {}
        nodes = []
        attributes = {}
        if State == "HEAT":
            Domoticz.Debug('CH On')
            attributes["attributes"] = {"activeHeatCoolMode": {"targetValue": "HEAT"},"activeScheduleLock": {"targetValue": "True"}}
        if State == "OFF":
            Domoticz.Debug('CH Off')
            attributes["attributes"] = {"activeHeatCoolMode": {"targetValue": "OFF"},"activeScheduleLock": {"targetValue": "False"}}
        nodes.append(attributes)
        response["nodes"] = nodes
        return response

    def isLight(self, Unit):
        Domoticz.Debug(str(self.lightsSet))
        if Devices[Unit].Type == 244 and Devices[Unit].SubType == 73 and Unit in self.lightsSet:
            Domoticz.Debug(str(Unit) + " is Active Light")
            return True
        elif Devices[Unit].Type == 241 and Devices[Unit].SubType == 4 and Unit in self.lightsSet:
            Domoticz.Debug(str(Unit) + " is RGB Light")
            return True
        elif Devices[Unit].Type == 241 and Devices[Unit].SubType == 8 and Unit in self.lightsSet:
            Domoticz.Debug(str(Unit) + " is WW/CW Light")
            return True
        else:
            return False

    def isThermostat(self, Unit):
        if Devices[Unit].Type == 242:
            return True
        else:
            return False

    def isActivePlug(self, Unit):
        Domoticz.Debug(str(self.activeplugsSet))
        if Devices[Unit].Type == 244 and Devices[Unit].SubType == 73 and Unit in self.activeplugsSet:
            return True
        else:
            return False

    def isHotWaterRelay(self, Unit):
        Domoticz.Debug(str(self.hwrelaySet))
        if Unit in self.hwrelaySet:
            return True
        else:
            return False

    def isCentralHeatingRelay(self, Unit):
        Domoticz.Debug(str(self.chrelaySet))
        if Unit in self.chrelaySet:
            return True
        else:
            return False

    def getDomoticzRevision(self):
        Revision = 0
        if 'DomoticzVersion' in Parameters:
            Domoticz.Log("DomoticzVersion Available " + Parameters['DomoticzVersion'])
            if Parameters['DomoticzVersion'].split(".")[0] > 4:
                Domoticz.Debug("Post-2020.2 build found")
                # We don't worry about revisions post 2020
                Revision = 9031
            else:
                Domoticz.Debug("Pre-2020.2 build found")
                Revision = Parameters['DomoticzVersion'].split(".")[1]
        else:
            Domoticz.Log("DomoticzVersion Not Available - Using JSON")
            url = 'http://127.0.0.1:' + Parameters['Mode2'] + '/json.htm?type=command&param=getversion'
            Domoticz.Log("Version URL: " + url)
            req = Request(url)
            try:
                r = urlopen(req).read().decode('utf-8')
                j = json.loads(r)
                Revision = j['Revision']
                Version = j['version']
                Domoticz.Debug("Domoticz Revision: " + str(Revision))
                Domoticz.Debug("Domoticz Version: " + Version + '->' + str(int(Version[-4:])))
                if int(Version[-4:]) > Revision:  # I've managed to create a build that has Version different to Revision so take the highest
                    Revision = int(Version[-4:])
            except HTTPError as e:
                if e.code == 401:
                    Domoticz.Error("Ensure you have 127.0.0.1 in your 'Local Networks' selection")
                else:
                    Domoticz.Error(str(e))
            except Exception as e:
                Domoticz.Error(str(e))
        Domoticz.Debug("Domoticz Revision: " + str(Revision))
        return Revision

    def GetSessionID(self):
            payload = {'sessions':[{'username':Parameters["Username"], 'password':Parameters["Password"]}]}
            headers = {'Content-Type': 'application/vnd.alertme.zoo-6.1+json',
                       'Accept': 'application/vnd.alertme.zoo-6.2+json',
                       'X-AlertMe-Client': 'Hive Web Dashboard'}
            url = 'https://api.prod.bgchprod.info:443/omnia/auth/sessions'
            req = Request(url, data = json.dumps(payload).encode('ascii'), headers = headers, unverifiable = True)
            r = urlopen(req).read().decode('utf-8')
            self.sessionId = json.loads(r)["sessions"][0]['sessionId']

    def GetWeatherURL(self):
            weather = False
            pc = str(Parameters['Mode3'])
            pc = pc.replace(" ","") # strip spaces from postcode (if existing)
            wurl = 'https://weather.prod.bgchprod.info/weather?postcode=' +str(pc) + '&country=GB'
            wreq = Request(wurl)

            try:
                weather = urlopen(wreq).read().decode('utf-8')
            except HTTPError as e:
                if e.code == 401: # Unauthorised - need new sessionId
                    self.onStop()
                    self.GetSessionID()
                    weather = urlopen(wreq).read().decode('utf-8')
                else:
                    Domoticz.Log(str(e))
            except Exception as e:
                Domoticz.Log(str(e))
            try:
                weather = json.loads(weather)['weather'] # get weather Object from the url response into a string for later	then return
            except Exception as e:
                Domoticz.Log(str(e))
            return weather

    def GetDevices(self):
            nodes = False
            headers = {'Content-Type': 'application/vnd.alertme.zoo-6.2+json',
                       'Accept': 'application/vnd.alertme.zoo-6.2+json',
                       'X-AlertMe-Client': 'swagger',
                       'X-Omnia-Access-Token': self.sessionId}
            url = 'https://api.prod.bgchprod.info:443/omnia/nodes'
            req = Request(url, headers = headers, unverifiable = True)
            try:
                r = urlopen(req).read().decode('utf-8')
            except HTTPError as e:
                if e.code == 401: # Unauthorised - need new sessionId
                    self.onStop()
                    self.GetSessionID()
                    r = urlopen(req).read().decode('utf-8')
                else:
                    Domoticz.Log(str(e))
            except Exception as e:
                Domoticz.Log(str(e))
            try:
                nodes = json.loads(r)['nodes']
            except Exception as e:
                Domoticz.Log(str(e))
            return nodes

_plugin = BasePlugin()

def onStart():
    _plugin.onStart()

def onStop():
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    _plugin.onHeartbeat()

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != '':
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug('Device count: ' + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug('Device:           ' + str(x) + ' - ' + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug('Device nValue:    ' + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug('Device LastLevel: ' + str(Devices[x].LastLevel))

def find_key_in_list(d, value):
    if isinstance(d, list):
        t = list(d)
        for v in d:
            if isinstance(v, dict):
                p = find_key(v, value)
                if not p:
                    t.remove(v)
        return t

def find_key(d, value):
    for (k, v) in d.items():
        if isinstance(v, dict):
            p = find_key(v, value)
            if p:
                return [k] + p
        elif v == value:
            return [k]
    
def merge_dicts(*dict_args):
    '''
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    '''
    result = { }
    for dictionary in dict_args:
        result.update(dictionary)
    return result

def rgb2hsv(r, g, b):
    r, g, b = r/255.0, g/255.0, b/255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx-mn
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g-b)/df) + 360) % 360
    elif mx == g:
        h = (60 * ((b-r)/df) + 120) % 360
    elif mx == b:
        h = (60 * ((r-g)/df) + 240) % 360
    if mx == 0:
        s = 0
    else:
        s = df/mx
    v = mx
    return h, s, v

# vim: tabstop=4 expandtab
