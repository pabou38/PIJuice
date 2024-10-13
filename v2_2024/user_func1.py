#!/usr/bin/python3

#############################
# system event tab:
#   associate events (charge, watchdog, button , ... ) to built in or user functions 1,2, 3 ..

# user scrip tab:
#  associate user functions to bash script
##############################

# called with sys.argv

# "PRESS" "SW3"
# "no_power"
# "low_charge" "93.0"   NOTE: keep sending every few sec
# "watchdog_reset" "True"
# 'sys_start', 'sys_stop'  then below. SW.  NOT sent for wakeup, only when using SW ??? but sent on wakeup if power ON


# NOTE: disable in GUI:
# no power (solar )
# sys_start (seems to ALSO be sent on RTC wakeup when power is ON. WTF
# sys_stop


"""
'{user_functions:', '{USER_FUNC8:', ',', 'USER_FUNC7:', ',', 'USER_FUNC15:', ',', 'USER_FUNC9:', ',', 'U                 SER_FUNC5:', ',', 'USER_FUNC11:', ',', 'USER_FUNC4:', ',', 'USER_FUNC10:', ',', 'USER_FUNC13:', ',', 'USER_FUNC                 14:', ',', 'USER_FUNC2:', ',', 'USER_FUNC6:', ',', 'USER_FUNC3:', ',', 'USER_FUNC1:', '/home/pi/beecamjuice/use                 r_func1.py,', 'USER_FUNC12:', '},', 

'system_task:', 
  '{wakeup_on_charge:', '{trigger_level:', '99,', 'enabled:', 'False},', 'enabled:', 'True,', 
   'min_bat_voltage:', '{threshold:', '3.2,', 'enabled:', 'True},', 
   'ext_halt_power_off:', '{enabled:', 'True,', 'period:', '30},', 
   'min_charge:', '{threshold:', '5,', 'enabled:', 'True},', 
   'watchdog:', '{enabled:', 'True,', 'period:', '3}},', 

'system_events:', 
  '{no_power:', '{enabled:', 'True,', 'function:', 'USER_FUNC1},', 
   'watchdog_reset:', '{enabled:', 'True,', 'function:', 'USER_FUNC1},', 
   'sys_stop:', '{enabled:', 'True,', 'function:', 'USER_FUNC1},', 
    'forced_sys_power_off:', '{enabled:', 'True,', 'function:', 'USER_FUNC1},', 
    'forced_power_off:', '{enabled:', 'True,', 'function:', 'USER_FUNC1},', 
    'button_power_off:', '{enabled:', 'True,', 'function:', 'USER_FUNC1},', 
    'low_charge:', '{enabled:', 'True,', 'function:', 'SYS_FUNC_HALT_POW_OFF},', 
    'sys_start:', '{enabled:', 'True,', 'function:', 'USER_FUNC1},', 
    'low_battery_voltage:', '{enabled:', 'True,', 'function:', 'SYS_FUNC_HALT_POW_OFF}}}'
"""

import sys
import logging
import urllib
#  python2 import httplib
import http.client
import os
import datetime
import time

import pijuice

while not os.path.exists('/dev/i2c-1'):
        time.sleep(0.1)

try:
        pj = pijuice.PiJuice(1, 0x14)
except:
        print("Cannot create pijuice object")
        logging.error('!!!!  cannot create pijuice in user function')
        send_pushover("PiJuice: cannot create PiJuice object in user function")

soc = pj.status.GetChargeLevel()
soc = "%0.0f" %(soc['data']) # str
print ("soc ", soc)
time.sleep(0.4)
vbat = pj.status.GetBatteryVoltage()
vbat = "%0.1f" %(vbat['data']/1000.0)
print ("vbat ", vbat)


# set some logging
logger = logging.getLogger('user_func1')
# not w by user pi. exception in beecamjuice if the log file is created here, and used later in beecamjuice
hdlr = logging.FileHandler('/home/pi/beecamjuice/logs/user_event1.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)


# sys.argv
s = "PiJuice user event 1 triggered from: %s\nsoc: %s, vbat: %s" %(str(sys.argv) ,soc, vbat)

# get some status
fault =  pj.status.GetFaultStatus()
s1 = "fault: %s" %fault

status  = pj.status.GetStatus()
s2 = "status: %s" %status

s = "%s\n%s\n%s" %(s,s1,s2)

# log source of event
print(s)
logger.info(s)

try:
	if sys.argv[1] not in ["no_power"]:
		# send pushover incl status, fault, source of event, soc 
		conn = http.client.HTTPSConnection("api.pushover.net:443")
		conn.request("POST", "/1/messages.json",
 	# urllib.urlencode({
		urllib.parse.urlencode({
  		  "token": "aoa3zx5s9bciiggixr5p2pbhfatdoo",
   		 "user": "uzae241vt7ii3v82t6f31368bt7qfo",
   	 	"message": s,
	 	 }), { "Content-type": "application/x-www-form-urlencoded" })
		conn.getresponse()

except Exception as e:
	s = "Exception sending pushover in user_func: %s" %str(e)
	print(s)
	logger.error(s)


"""
urllib has been split up in Python 3.

The urllib.urlencode() function is now urllib.parse.urlencode(),

the urllib.urlopen() function is now urllib.request.urlopen().
"""
