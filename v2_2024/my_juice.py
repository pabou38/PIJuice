#!/usr/bin/python3

#https://github.com/PiSupply/PiJuice/tree/master/Software

#PiJuiceStatus Functions for dynamically controlling and reading status of PiJuice features.
#PiJuiceRtcAlarm Functions for setting-up real time clock and wake-up alarm.
#PiJuicePower Power management functions.
#PiJuiceConfig Functions for static configuration that mostly involves non-volatile data that saves in EEPROM.

# https://github.com/PiSupply/PiJuice/issues/770
# https://github.com/PiSupply/PiJuice/issues/186
# https://github.com/PiSupply/PiJuice/issues/91#issuecomment-381324352
# https://raspberrypi-guide.github.io/other/boot-automation-pijuice Turn off Raspberry Pi when battery too low, Turning the Raspberry Pi on and off automatically
# https://github.com/PiSupply/PiJuice/issues/357  Always Wakeup on Charge
# https://github.com/PiSupply/PiJuice/issues/449

# After the initial set of system time using the Linux date command and the copy to PiJuice RTC
# sudo hwclock -w, you simply just need to run at system startup do a 'sudo hwclock -s' to copy the time from the RTC to the system clock e.g. in /etc/rc.local.
# This is also assuming that your ID EEPROM is set to 0x50 in which case the RTC driver is loaded at boot.
# lsmod to check module  Force loading the module by adding the following line to /boot/config.txt:
# dtoverlay=i2c-rtc,ds1339
# i2cdetect must shows UU instead of 68 https://github.com/PiSupply/PiJuice/issues/186


import os
import pijuice
import time
import http.client, urllib

def get_juice():

	while not os.path.exists('/dev/i2c-1'):
		time.sleep(0.1)
	try:
		pj = pijuice.PiJuice(1, 0x14)
		return(pj)

	except Exception as e:
		# cannot use internal led to signal error. pj not created
		print("Cannot create pijuice object", str(e))
		return(None)


####################
# status
####################

# Gets basic PiJuice status information about power inputs, battery and events

#is_fault is True if there are faults or fault events waiting to be read or False if there are no faults and no fault events.
#is_button is True if there are button events, False if not.
#battery_status is a string constant that describes the current battery status, one of four: 'NORMAL', 'CHARGING_FROM_IN', 'CHARGING_FROM_5V_IO', 'NOT_PRESENT'.

# PIjuice micro usb
#power_input_status is a string constant that describes current status of USB Micro power input, one of four: 'NOT_PRESENT', 'BAD', 'WEAK', 'PRESENT'.

# power from PI micro usb
#5v_power_input_status: is a string constant that describes current status of the 5V GPIO power input, one of four: 'NOT_PRESENT', 'BAD', 'WEAK', 'PRESENT'.

def get_status(pj):

	ret = pj.status.GetStatus()

	if ret["error"] == 'NO_ERROR':
		return(ret["data"])
	else:
		return(None)


# charge_level is the percentage of charge, [0 - 100]%
# the temperature in Celsius.
# Voltage in millivolts (mV).
# Value returned is voltage supplied from the GPIO power output from the PiJuice or when charging, voltage value returned is supplied voltage. Value returned is in millivolts (mV).
# Value returned is current supplied from the GPIO power output from the PiJuice or when charging, current value returned is supplied current. Value returned is in milliamps (mA).



# iio 200 ma, Vio 5V  ibat 300 ma when not charging,  -2000 when charging
# Vbat is the on-board battery voltage and ibat is the current that is being supplied from the battery.

# vio is the voltage that is on the IO pin weather this is input or output and the iio is the current being provided $
# When reading analog read on IO1 it will output the same as vio.

def get_battery(pj):

	ret = pj.status.GetChargeLevel()
	if ret["error"] == 'NO_ERROR':
		soc = "%0.0f" %(ret['data'])
		soc = int(soc)
		print ("soc: ", soc)
	else:
		print("error soc")
		soc = None

	ret = pj.status.GetBatteryTemperature()
	if ret["error"] == 'NO_ERROR':
		temp = "%0.0f" %(ret['data'])
		temp = int(temp)
		print ("temp: ", temp)
	else:
		print("error temp")
		temp = None

	ret = pj.status.GetBatteryVoltage()
	if ret["error"] == 'NO_ERROR':
		mv = "%0.0f" %(ret['data'])
		mv = int(mv)
		print ("battery voltage mv: ", mv)
	else:
		print("error battery voltage")
		mv = None


	ret = pj.status.GetIoVoltage()
	if ret["error"] == 'NO_ERROR':
		iomv = "%0.0f" %(ret['data'])
		iomv = int(iomv)
		print ("supply/input voltage mv: ", iomv)
	else:
		print("error io voltage")
		iomv = None

	# current seems 0 when powered from pijuice micro USB 
	ret = pj.status.GetIoCurrent()
	if ret["error"] == 'NO_ERROR':
		ioma = "%0.0f" %(ret['data'])
		ioma = int(ioma)
		print ("supplied/drawn current ma:  (0 when powered from USB ?)", ioma)
	else:
		print("error io amps")
		ioma = None


	return(soc,temp,mv, iomv, ioma)



#############
# fault status
#############

#Get the current fault status of PiJuice HAT.
#button_power_off
#forced_power_off
#forced_sys_power_off
#watchdog_reset
#battery_profile_invalid: ['NORMAL', 'SUSPEND', 'COOL', 'WARM']

# {} when no fault
def get_fault_status(pj):

	ret = pj.status.GetFaultStatus()
	if ret["error"] == 'NO_ERROR':
		fault = ret['data']
		#print ("fault status: ", fault)
		return(fault)
	else:
		return(None)

#############
# reset fault flag
# ??????
#############

def reset_fault_flag(pj):
	pj.status.ResetFaultFlags(['powerOffFlag', 'sysPowerOffFlag'])



# GetButtonEvents()
# AcceptButtonEvent(button)


#############
# led
#############
# SetLedState(led, rgb)
# GetLedState(led)
# SetLedBlink(led, count, rgb1, period1, rgb2, period2)
# GetLedBlink(led)


##############
# IO
##############
# GetIoDigitalInput(pin)
# SetIoDigitalOutput(pin, value)
# GetIoDigitalOutput(pin)
# GetIoAnalogInput(pin)
# SetIoPWM(pin, dutyCircle)
# GetIoPWM(pin)


###################
# RTC alarm
###################
# PiJuice RTC Alarm functions allow you to get the current status of the alarm flag as well as setting the alarm and enabling the wakeup function. You can also get current time set in the RTC as well as setting the time. PiJuice RTC Alarm functions allow you to get the current status of the alarm flag as well as setting the alarm and enabling the wakeup function. You can also get current time set in the RTC as well as setting the time. 


####################
# RTC status
####################
# checks to see if wakeup has been enabled and if the wakeup alarm flag has been set.
def get_RTC_status(pj):

	ret = pj.rtcAlarm.GetControlStatus()
	if ret["error"] == 'NO_ERROR':
		wakeup_status = ret['data']
		print ("RTC wakeup status: ", wakeup_status)
		return(wakeup_status)
	else:
		return(None)

############## ????
# ClearAlarmFlag()

####################
# time
####################


# Returns current time and date set in RTC:
# GetTime() 

# Sets time and date as per values set in arguments.
# {'second':second, 'minute':minute, 'hour':hour, 'weekday':(weekday()+1) % 7 + 1, 'day':day, 'month':month, 'year':year, 'subsecond':microsecond//1000000}
# SetTime(dateTime)


####################
# enable (RTC) wakeup
####################
# RTC alarm (not wakeuponcharge)
# NEED TO ENABLE AT EACH BOOT FOR REPEATED WAKEUP (unless eeprom 52)

# When the alarm goes off it will check to see if wakeup enabled is True.
# I INTERPRET as : this is processing on STM32

# Enable wakeup, otherwise power to the RPi will not be applied when the RTC alarm goes off
# Note that we added the line pj.rtcAlarm.SetWakeupEnabled(True) because when setting the Wakeup alarm for repeated wakeup, the Wakeup enabled capability is disabled due to the Raspbian RTC clock initialisation resetting the PiJuice firmware.
# Repeated Wakeup
# When setting the Wakeup alarm for a repeated wakeup, after the initial reboot the Wakeup enabled capability is disabled due to the Raspbian RTC clock initialisation resetting the bit in the PiJuice firmware. To overcome this you will need to run a script to re-enable the wakeup-enable capability.

def enable_wakeup(pj, b):
	ret= pj.rtcAlarm.SetWakeupEnabled(b)
	return(ret['error'] == 'NO_ERROR')



####################
# RTC wakeup
####################


# Get values for current alarm that has been set.
# 'data': {'second': 0, 'minute': 0, 'hour': 'EVERY_HOUR', 'day': 'EVERY_DAY'}, 'error': 'NO_ERROR'}
# GetAlarm()
def get_alarm(pj):
	ret = pj.rtcAlarm.GetAlarm()
	if ret['error'] == 'NO_ERROR':
		return(ret["data"])
	else:
		return(None)


#  Set the alarm based on arguments set
# {'second': 0, 'minute': 0, 'hour': 'EVERY_HOUR', 'day': 'EVERY_DAY'}
# every year,month,day,hour
# second = 0
# mn = now + sleep modulo 60
def set_alarm(pj, a):
	print("set alarm", a)

	ret = pj.rtcAlarm.SetAlarm(a)
	if ret['error'] != 'NO_ERROR':
		return(False)
	else:
		return(True)


####################
# poweroff delay
####################
# Removes power from the PiJuice to the GPIO pins i.e Raspberry Pi. Delay is used here to give the Raspberry Pi enough time to do a safe shutdown before power has been removed. Delay value is should be written in seconds.
# delay to cut power to PI after software halt or button (sudo halt, sudo shutdown -h etcc..)

# I assume this is a config, can also be done in GUI aka Software Halt power off
def set_poweroff(pj, delay=30):
	ret = pj.power.SetPowerOff(delay)
	return (ret['error'] == 'NO_ERROR')

def get_poweroff(pj):
	ret = pj.power.GetPowerOff()
	if ret['error'] == 'NO_ERROR':
		return(ret["data"])
	else:
		return(None)

####################
# wakeup on charge
####################

# Used to wakeup the Raspberry Pi when the battery charge level reaches a certain percentage as set in the passed argument
# Wakeup on charge only works when the PiJuice 5V is off when charging is detected.
# At wakeup the Wakeup on charge flag is cleared so it has to be set again before shutdown.

# ADDITIONAL to RTC, so mess up with regular wakeup
# when power present on pijuice usb (4.5v to 10V)
# 0 means regardless of soc, incl no battery
# disable in GUI

def get_wakeuponcharge(pj):
	ret = pj.power.GetWakeUpOnCharge()
	if ret['error'] == 'NO_ERROR':
		return(ret["data"])
	else:
		return(None)

def set_wakeuponcharge(pj,p):
	ret = pj.power.SetWakeUpOnCharge(p)
	return(ret['error'] == 'NO_ERROR')

####################
# watchdog
####################


# It defines the time after which it will power cycle if it does not receive a heartbeat signal. The time step is in minutes
# seems value from GUI is the same as from API
def set_watchdog(pj,mn):
	ret = pj.power.SetWatchdog(mn)
	return(ret['error'] == 'NO_ERROR')


def get_watchdog(pj):
	ret = pj.power.GetWatchdog()
	if ret['error'] == 'NO_ERROR':
		return(ret["data"])
	else:

		return(None)

####################
# utils
####################

# get ALL possible status, as str
def get_all_status_str(pj):

# Gets basic PiJuice status information about power inputs, battery and events.
	txt = "basic status: %s\n" %pj.status.GetStatus()

# {'data': {'button_power_off': True, 'forced_power_off': True}, 'error': 'NO_ERROR'}
# button_power_off forced_power_off forced_sys_power_off watchdog_resetbattery_profile_invalid: ['NORMAL', 'SUSPEND', 'COOL', 'WARM']
	txt = "%sfault status: %s\n" %(txt,pj.status.GetFaultStatus())

# PiJuice RTC Alarm functions allow you to get the current status of the alarm flag as well as setting the alarm and enabling the wakeup function.
	txt = "%sRTC control status: %s\n" %(txt,pj.rtcAlarm.GetControlStatus())

	txt = "%sRTC alarm value: %s\n" %(txt,pj.rtcAlarm.GetAlarm())

	txt = "%sPowerOff value: %s\n" %(txt,pj.power.GetPowerOff())

	txt = "%sWakeUpOnCharge value: %s\n" %(txt,pj.power.GetWakeUpOnCharge())

	txt = "%sWatchdog value: %s\n" %(txt,pj.power.GetWatchdog())

	return(txt)

def log(txt):
	with open('/home/pi/beecamjuice/logs/wakeuptest.log','a') as f:
		f.write(txt)




#################
# test wakeup
#################
# soc 99% to 90% 15h to 7h ie 16h, every 15mn
# ie 0.6% soc / h

def test_wakeup(delta):
	import datetime
	import sys
	import subprocess
	import RPi.GPIO as GPIO

	import pushover

	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	# connect to ground to keep running
	GPIO.setup(26,GPIO.IN,pull_up_down=GPIO.PUD_UP)
	halt = GPIO.input(26)

	keep_running = (halt == 0)

	if keep_running:
		print("!!!!KEEP RUNNING. exit")
		sys.exit()


	# rc ??  make sure all pi is init (incl networking)
	print("sleeping to init PI")
	time.sleep(30)


# This script is started at reboot by cron.
# Since the start is very early in the boot sequence we wait for the i2c-1 device
	while not os.path.exists('/dev/i2c-1'):
		time.sleep(0.1)

	try:
		pj = pijuice.PiJuice(1, 0x14)
	except:
		s = "Cannot create pijuice object"
		print(s)
		log(s)
		pushover.send_pushover(s)

		sys.exit()


	i = 0 # status OK retries
	while pj.status.GetStatus()['error'] != 'NO_ERROR':
		i = i  + 1
		if i == 10:
			s = "status not ok. retry: %d. REBOOT" %(i)
			print(s)
			log(s)
			pushover.send_pushover(s)

			# hope
			subprocess.call(["sudo", "reboot"])


		else:
			s = "status not ok. retry: %d. retry" %(i)
			print(s)
			log(s)
			time.sleep(1)

	# status OK
	print("PIJuice status OK. %s retries" %i)


	txt = "start juice test wakeup. before time synch: %s.\ndelta mn: %d\n" %(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), delta)
	txt = txt + get_all_status_str(pj)
	print(txt)
	log(txt)
	pushover.send_pushover(txt)


	# synch. check output 

	# error only seen in stderr (if redirected to file)
	#subprocess.call(["sudo", "hwclock", "--hctosys"]) 

	try:
		data = subprocess.check_output(['sudo', 'hwclock', "--hctosys"])
		data = data.decode('utf-8')
		# empty if OK
		s = "hctosys: %s" %data
		print(s)
		log(s)

	except Exception as e:
		s = "Exception setting hwclock: %s" %str(e)
		print(s)
		log(s)

	# flag seem to indicate whether wakeup ir caused by RTC
	pj.rtcAlarm.ClearAlarmFlag()

	# incl various data in log, push
	(soc,temp,mv, iomv, ioma) = get_battery(pj)


# Set RTC alarm 5 minutes from now
# RTC is kept in UTC
	a={}
	a['year'] = 'EVERY_YEAR'
	a['month'] = 'EVERY_MONTH'
	a['day'] = 'EVERY_DAY'
	a['hour'] = 'EVERY_HOUR'
	t = datetime.datetime.utcnow()
	a['minute'] = (t.minute + delta) % 60
	a['second'] = 0

	status = pj.rtcAlarm.SetAlarm(a)

	if status['error'] != 'NO_ERROR':
		s = 'Cannot set RTC alarm. EXIT'
		log(s)
		print(s)
		pushover.send_pushover(s)
		sys.exit()

	next_mn = a["minute"]



# Enable wakeup, otherwise power to the RPi will not be applied when the RTC alarm goes off
# possibly persistent, but better safe tha sorry
	pj.rtcAlarm.SetWakeupEnabled(True)
	time.sleep(0.4)


# PiJuice shuts down power to Rpi after 20 sec from now. This leaves sufficient time to execute the shutdown sequence
	pj.power.SetPowerOff(20)
	time.sleep(0.4)

# seem need to be set at each boot
# need to be enabled, to recover from depleted battery ?
#   or just disable. a depleted battery will eventually recharge, and  RTC wakeup sequence will restart
# if enabled, should not triger wakeup when battery is 60% and solar are charging via pijuice microusb (ie mess with RTC wakeup)
# enable function of current soc ?
	"""
	if soc is None or soc < 10:
		pj.power.SetWakeUpOnCharge(20)

	else:
		pj.power.SetWakeUpOnCharge(98)

	time.sleep(0.4)
	"""

	txt = "powerdown: %s.retry: %d. next mn %d. soc: %d%% ioma: %d\n" \
       	 %(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),i, next_mn, soc, ioma)

	txt = txt + get_all_status_str(pj)

	print(txt)
	log(txt)
	pushover.send_pushover(txt)

	subprocess.call(["sudo", "poweroff"])



if __name__ == "__main__":

	delta= 15
	test_wakeup(delta)
	# wil shutdown anyway

	sys.exit(1)


	pj= get_juice()
	print("status", get_status(pj))

	print("battery:", get_battery(pj))


	print("fault status", get_fault_status(pj))

	print("power off delay", get_poweroff(pj))
	print("wakeup on charge", get_wakeuponcharge(pj))
	#power off delay [255]
	#wakeup on charge 127

	# same as GUI
	print("watchdog", get_watchdog(pj))

	d = 30
	print("set poweroff delay to %dsec" %d)
	set_poweroff(pj,d)
	x = 10

	print("sleep for %dsec" %x)
	time.sleep(x)

	print("power off delay", get_poweroff(pj))

	set_wakeuponcharge(pj, 20)
	print("wakeup on charge", get_wakeuponcharge(pj))


"""

"""
