#!/usr/bin/python3

# to get local ssid
# iwgetid -r
# netsh wlan show interfaces

import subprocess
import shutil

###############
# get ssid
###############
def get_ssid():

	#data = subprocess.check_output(['netsh', 'WLAN', 'show', 'interfaces'])
	data = subprocess.check_output(['iwgetid', '-r'])
	#print(data) # b'Freebox-382B6B\n'
	data = data.decode('utf-8')
	print(data)
	return(data)


##############
# get file system free in %
##############
def get_fs_free(fs="/"):
	total, used, free = shutil.disk_usage(fs)
	return(int(100*free/total))


if __name__ == "__main__":
	wifi = get_ssid()
	if "Freebox" in wifi:
		print("immeuble end S")
	else:
		print("Meaudre")

	fs = get_fs_free()
	print("%d %% free" %fs)
