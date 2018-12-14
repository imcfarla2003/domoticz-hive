# domoticz-hive
Domoticz plugin for Hive

Place plugin.py in a folder called Hive in the plugins directory in your domoticz folder.
i.e.
.../domoticz/plugins/Hive/plugin.py

restart domoticz <- important otherwise the plugin will not be detected.

Then go to setup and you should be able to choose Hive plugin in the Type dropdown.

- Add your Hive username and password and click Add at the bottom.
- The Heartbeat multiplier defines how many heartbeats before it processes the data from Hive.  I decided to use 6 (60s) as the default.  This is a good balance between the dashboard updating when using the hive app and how many updates you request.
- If you are using version 3.8790 or below (older than current stable) you will also need to specify the Domoticz Port and check that password-less access is available (add 127.0.0.1 into the "Local Networks" box on the Settings page) 

Notes: 
Multizone heating is not yet supported (waiting for an output from collect_json.py)

Works for Active Light Dimmable, Cool to Warm and Colour Changing lights now.

ActivePlug is now working.

