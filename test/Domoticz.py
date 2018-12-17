Devices = {}
debugLevel = 0

def Log(message):
    print("Log: " + message)

def Debug(message):
    if debugLevel > 0:
        print("Debug: " + message)

def Error(message):
    print("Error: " + message)

def Debugging(level):
    debugLevel = level
    print("Debug Level: " + str(debugLevel))

class Device:
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
        self.Name = Name
        if debugLevel > 0:
            print("New Device: " + self.DeviceID)

    def Create(self):
        Devices[len(Devices)+1] = self
        if debugLevel > 0:
            print("Create Device: " + self.DeviceID)

    def Update(self, nValue, sValue, SignalLevel=0, BatteryLevel=0, TimedOut=0):
        self.sValue = sValue
        self.nValue = nValue
        self.TimedOut = TimedOut
        if debugLevel > 0:
            print("Update Device: " + self.DeviceID)

# vim: tabstop=4 expandtab
