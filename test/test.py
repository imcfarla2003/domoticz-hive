import sys
import Domoticz

if len(sys.argv) < 3:
    print("Basic Usage:    " + sys.argv[0] + " <Hive username> <Hive password>")
    print("With Heartbeat: " + sys.argv[0] + " <Hive username> <Hive password> 1")
    exit()

Parameters = {}
Parameters["Username"] = sys.argv[1]
Parameters["Password"] = sys.argv[2]
Parameters["Mode1"] = 1 #Multiplier
Parameters["Mode2"] = '8080' #Port
Parameters["Mode3"] = 'CB24' #Postcode
Parameters["Mode6"] = '62' #Debug
#Parameters["Mode6"] = 'Normal' #No Debug
Parameters["DomoticzVersion"] = '4.10263' #Domoticz Version

Devices = Domoticz.Devices

filename = "../plugin.py"
exec(open(filename).read())

print("Starting")
try:
    onStart()
except Exception as e:
    print(traceback.format_exc())
print("Devices")
for unit in Devices:
    print("    "+Devices[unit].Name)
if len(sys.argv) >3:
    if sys.argv[3] == '1':
        print("Heartbeat")
        onHeartbeat()
print("Stopping")
onStop()
Domoticz.Debugging(1)
DumpConfigToLog()
# vim: tabstop=4 expandtab
