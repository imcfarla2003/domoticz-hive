# domoticz-hive
Domoticz plugin for Hive

Place plugin.py in a folder called Hive in the plugins directory in your domoticz folder.
i.e.
.../domoticz/plugins/Hive/plugin.py

restart domoticz <- important otherwise the plugin will not be detected.
Then go to setup and you should be able to choose Hive plugin in the Type dropdown.

- Add your Hive username and password and click Add at the bottom.
- The Heartbeat multiplier defines how many heartbeats before it processes the data from Hive
I started off with 6 (60s) as the default but now I have added in light control this really should just be 1 (10s) otherwise you wait too long before the dashboard updates to say you have switched on a light.
- You will also need to specify the Domoticz Port and check that password-less access is available (add 127.0.0.1 into the "Local Networks" box on the Settings page) if you are using version 3.8790 or below

Note:
Only works for Active Light Dimmable as I haven't got any Cool to Warm or Colour Changing

ActivePlug is now working.

