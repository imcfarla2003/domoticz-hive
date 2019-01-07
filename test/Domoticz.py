import sys
from urllib.request import Request, urlopen

Devices = {}
debugLevel = 0
# this is a pointer to the module object instance itself.
this = sys.modules[__name__]

def Log(message):
    print("Log: " + message)

def Debug(message):
    if this.debugLevel > 0:
        print("Debug: " + message)

def Error(message):
    print("Error: " + message)

def Debugging(level):
    this.debugLevel = level
    print("Debug Level: " + str(this.debugLevel))

class Connection:
    Name = ''
    Transport = ''
    Protocol = ''
    Address = ''
    Port = ''
    def __init__(self, Name, Transport, Protocol, Address, Port):
        self.Name = Name
        self.Transport = Transport
        self.Protocol = Protocol
        self.Address = Address
        self.Port = Port
        print("Connection: " + self.Name)

    def Connect(self):
        print("Connect: " + self.Name)

    def Send(self, URL, Headers, Data):
       req = Request(self.Address + ":" + self.Port + URL, data = Data, headers = Headers, unverifiable = True)
       self.results = req.read()

class Device:
    ID = 0
    DeviceID = ''
    Type = ''
    Subtype = ''
    Name = ''
    sValue = ''
    nValue = 0
    TimedOut = 0
    LastLevel = ''

    def __init__(self, Name, DeviceID, Unit, Type = "", Subtype = "", TypeName = "", Switchtype = 0):
        self.DeviceID = DeviceID
        self.Type = Type
        self.Subtype = Subtype
        if TypeName == "Switch":
            self.Type = 244
            self.Subtype = 73
        elif TypeName == "Temperature":
            self.Type = 80 
            self.Subtype = 5
        else:
           pass 
        self.Name = Name
        if debugLevel > 0:
            print("New Device: " + self.DeviceID)

    def Create(self):
        self.ID = len(Devices)+1
        Devices[self.ID] = self
        if debugLevel > 0:
            print("Create Device: " + self.DeviceID)

    def Update(self, nValue, sValue, SignalLevel=0, BatteryLevel=0, TimedOut=0):
        self.sValue = sValue
        self.nValue = nValue
        self.TimedOut = TimedOut
        if debugLevel > 0:
            print("Update Device: " + self.DeviceID)

# vim: tabstop=4 expandtab
