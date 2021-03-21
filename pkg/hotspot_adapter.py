"""Hotspot adapter for WebThings Gateway."""

# A future release will no longer show privacy sensitive information via the debug option. 
# For now, during early development, it will be available. Please be considerate of others if you use this in a home situation.


from __future__ import print_function

import os
#from os import path
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
#try:
#    sys.path.append(os.path.join(os.sep,'home','pi','.webthings','addons','hotspot','lib'))
#except:
#    print("couldn't add extra path")
import json
import time
import queue
import socket
import asyncio
import logging
import requests
import threading
import subprocess
from subprocess import call, Popen
#from collections import namedtuple


try:
#    from .intentions import *
#    print("succesfully imported intentions.py file")
    pass
except Exception as ex:
    print("ERROR loading intentions.py: " + str(ex))
    
from gateway_addon import Database, Adapter
from .util import *
#from .hotspot_device import *
#from .hotspot_notifier import *

try:
    #from gateway_addon import APIHandler, APIResponse
    #from .hotspot_api_handler import * #CandleManagerAPIHandler
    #print("HotspotAPIHandler imported")
    pass
except Exception as ex:
    print("Unable to load HotspotAPIHandler (which is used for UI extention): " + str(ex))



_TIMEOUT = 3

_CONFIG_PATHS = [
    os.path.join(os.path.expanduser('~'), '.webthings', 'config'),
]

if 'WEBTHINGS_HOME' in os.environ:
    _CONFIG_PATHS.insert(0, os.path.join(os.environ['WEBTHINGS_HOME'], 'config'))



class HotspotAdapter(Adapter):
    """Adapter for Snips"""

    def __init__(self, verbose=True):
        """
        Initialize the object.
        
        verbose -- whether or not to enable verbose logging
        """
        print("Starting Hotspot addon")
        #print(str( os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib') ))
        self.pairing = False
        self.DEBUG = False
        self.DEV = False
        self.addon_name = 'hotspot'
        self.name = self.__class__.__name__ # HotspotAdapter
        #print("self.name = " + str(self.name))
        Adapter.__init__(self, self.addon_name, self.addon_name, verbose=verbose)
        #print("Adapter ID = " + self.get_id())

        #os.environ["LD_LIBRARY_PATH"] = os.path.join(self.user_profile['addonsDir'],self.addon_name,'snips')

        # Get initial audio_output options
        #self.audio_controls = get_audio_controls()
        #print("audio controls: " + str(self.audio_controls))



        # Some paths
        print("self.user_profile:")
        print(str(self.user_profile))
        self.addon_path = os.path.join(self.user_profile['addonsDir'], self.addon_name)
        #self.dnsmasq_log_path = os.path.join(self.addon_path,"snips","response.wav")
        self.data_dir_path = os.path.join(self.user_profile['dataDir'], self.addon_name)
        self.dnsmasq_conf_file_path = os.path.join(self.data_dir_path, "dnsmasq.conf")
        self.dnsmasq_log_file_path = os.path.join(self.data_dir_path, "dnsmasq_log.conf")
        self.hostapd_conf_file_path = os.path.join(self.data_dir_path, "hostapd.conf")
        

        # Make sure the data directory exists
        try:
            if not os.path.isdir(self.data_dir_path):
                os.mkdir( self.data_dir_path )
                print("data directory did not exist, created it now")
        except:
            print("Error: could not make sure data dir exists.")


        # Get persistent data
        try:
            self.persistence_file_path = os.path.join(self.data_dir_path, 'persistence.json')
        except:
            try:
                print("setting persistence file path failed, will try older method.")
                self.persistence_file_path = os.path.join(os.path.expanduser('~'), '.webthings', 'data', 'hotspot','persistence.json')
            except:
                print("Double error making persistence file path")
                self.persistence_file_path = "/home/pi/.webthings/data/hotspot/persistence.json"
        
        if self.DEBUG:
            print("Current working directory: " + str(os.getcwd()))
        
        first_run = False
        try:
            with open(self.persistence_file_path) as f:
                self.persistent_data = json.load(f)
                if self.DEBUG:
                    print("Persistence data was loaded succesfully.")
                        
        except:
            first_run = True
            print("Could not load persistent data (if you just installed the add-on then this is normal)")
            try:
                unique_id = generate_random_string(4)
                self.persistent_data = {'unique_id':unique_id}
            except Exception as ex:
                print("Error creating initial persistence variable: " + str(ex))
        


        self.mac = getmac("wlan0")
        self.mac_zero = self.mac.replace(self.mac[len(self.mac)-1], '0')

        print("mac = " + str(self.mac))
        print("mac_zero = " + str(self.mac_zero))
        self.name_server = "87.118.100.175" # German Privacy Foundation
        self.country_code = "NL"
        self.hotspot_name = "Candle"
        self.hotspot_password = "iloveprivacy"
        self.ip_address = "192.168.1.166"
        
        
        try:
            if 'unique_id' not in self.persistent_data: # to remember what the main hotspot server is, for satellites.
                print("unique_id was not in persistent data, adding it now.")
                self.persistent_data['unique_id'] = generate_random_string(4)
        except:
            print("Error fixing unique_id in persistent data")

       

        
        
        # LOAD CONFIG
        try:
            self.add_from_config()
        except Exception as ex:
            print("Error loading config: " + str(ex))
            
        self.ssid = self.hotspot_name + " " + self.persistent_data['unique_id'] + "_nomap"
        print("ssid = " + str(self.ssid))
        
        
        filename = "/etc/resolv.conf"
        with open(filename) as f:
            content = f.readlines()

        for line in content:
            #print(line)
            if line.startswith( "nameserver " ):
                self.name_server = line.split(" ")[1]
                print("name server: " + str(self.name_server))
            

        if self.DEBUG:
            print("self.persistent_data is now:")
            print(str(self.persistent_data))



        # Create Hotspot device
        try:
            #hotspot_device = HotspotDevice(self, self.audio_output_options)
            #self.handle_device_added(hotspot_device)
            if self.DEBUG:
                print("Hotspot thing created")
        except Exception as ex:
            print("Could not create hotspot device:" + str(ex))


        # Stop Snips until the init is complete (if it is installed).
        try:
            #os.system("pkill -f snips") # Avoid snips running paralel
            #self.devices['hotspot'].connected = False
            #self.devices['hotspot'].connected_notify(False)
            pass
        except Exception as ex:
            print("Could not stop Snips: " + str(ex))
        


        #
        # Create UI
        #
        # Even if the user doesn't want to see a UI, it may be the case that the HTML is still loaded somewhere. So the API should be available regardless.
        
        try:
            #self.extension = HotspotAPIHandler(self, verbose=True)
            #self.manager_proxy.add_api_handler(self.extension)
            if self.DEBUG:
                print("Extension API handler initiated")
        except Exception as e:
            print("Failed to start API handler (this only works on gateway version 0.10 or higher). Error: " + str(e))

    
            
        # Get network info
        try:
            self.update_network_info()
            self.previous_hostname = self.hostname
        except Exception as ex:
            print("Error getting ip address: " + str(ex)) 
        
        
        time.sleep(1)

            
        # Create notifier
        try:
            #self.voice_messages_queue = queue.Queue()
            #self.notifier = HotspotNotifier(self,self.voice_messages_queue,verbose=True) # TODO: It could be nice to move speech completely to a queue system so that voice never overlaps.
            pass
        except:
            print("Error creating notifier")

        # Start the internal clock which is used to handle timers. It also receives messages from the notifier.
        if self.DEBUG:
            print("Starting the internal clock")
        try:
            #self.t = threading.Thread(target=self.clock, args=(self.voice_messages_queue,))
            #self.t.daemon = True
            #self.t.start()
            pass
        except:
            print("Error starting the clock thread")


            
        time.sleep(1.34)
        
        # Set thing to connected state
        try:
            #self.devices['hotspot'].connected = True
            #self.devices['hotspot'].connected_notify(True)
            pass
        except Exception as ex:
            print("Error setting device details: " + str(ex))
            
        #time.sleep(5.4) # Snips needs some time to start



        #
        # DNSMASQ CONF

        dnsmasq_conf_string = """interface=lo,uap0
no-dhcp-interface=lo,wlan0
bind-interfaces
server=127.0.0.1
#server=192.168.12.1
server=""" + self.name_server

        dnsmasq_conf_string += """#server=8.8.8.8
domain-needed
bogus-priv
dhcp-range=192.168.12.2,192.168.12.30,255.255.255.0,12h
dhcp-option=3,192.168.12.1
dhcp-option=6,192.168.12.1,""" + self.name_server

#        dnsmasq_conf_string += """#dhcp-option=dns-server,192.168.12.1,192.168.2.2,8.8.8.8
#address=/gw.wlan/192.168.12.1
#log-queries
#log-dhcp
#log-facility=./dnsmasq.log"""

        print("")
        print("___dnsmasq_conf_string___")
        print(str(dnsmasq_conf_string))
        textfile = open(self.dnsmasq_conf_file_path, "w")
        a = textfile.write(dnsmasq_conf_string)
        textfile.close()
            


        
        
        #
        # HOSTAPD CONF
        
        hostapd_conf_string = """interface=uap0
driver=nl80211
bssid=""" + self.mac_zero + "\n"
        
        hostapd_conf_string += "ssid=" + self.ssid + "\n"
        #dnsmasq_conf_string += "#channel=" + self.wifi_channel # not necessary, will always be the same as the wifi
        hostapd_conf_string += "country_code=" + self.country_code + "\n"
        
        hostapd_conf_string += """hw_mode=g
channel=1
auth_algs=1
wpa=2
wpa_passphrase=""" + self.hotspot_password + "\n"

        hostapd_conf_string += """wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP"""

        print("")
        print("___hostapd_conf_string___")
        print(str(hostapd_conf_string))
        textfile = open(self.hostapd_conf_file_path, "w")
        a = textfile.write(hostapd_conf_string)
        textfile.close()


        self.save_persistent_data()
        print("end of init")

        self.start_hostapd()



#
#  GET CONFIG
#

    # Read the settings from the add-on settings page
    def add_from_config(self):
        """Attempt to add all configured devices."""
        try:
            database = Database('hotspot')
            if not database.open():
                print("Could not open settings database")
                return
            
            config = database.load_config()
            database.close()
            
        except:
            print("Error! Failed to open settings database.")
        
        if not config:
            print("Error loading config from database")
            return
        
        #print(str(config))

        if 'Debugging' in config:
            print("-Debugging was in config")
            self.DEBUG = bool(config['Debugging'])
            if self.DEBUG:
                print("Debugging enabled")        
        
        
        
        try:
            # Store the settings that were changed by the add-on.
            if store_updated_settings:
                if self.DEBUG:
                    print("Storing overridden settings")

                database = Database('hotspot')
                if not database.open():
                    print("Error, could not open settings database to store modified settings")
                    #return
                else:
                    database.save_config(config)
                    database.close()
                    if self.DEBUG:
                        print("Stored overridden preferences into the database")
        except:
            print("Error! Failed to store overridden settings in database.")
        
        
        
        # Hotspot name
        try:
            if 'Hotspot name' in config:
                if self.DEBUG:
                    print("-Hotspot name is present in the config data.")
                self.hotspot_name = str(config['Hotspot name'])
        except Exception as ex:
            print("Error loading hotspot name from config: " + str(ex))
        
        
        
        # Hotspot password
        try:
            if 'Hotspot password' in config:
                if self.DEBUG:
                    print("-Hotspot password is present in the config data.")
                self.hotspot_password = str(config['Hotspot password'])
        except Exception as ex:
            print("Error loading hotspot password from config: " + str(ex))
        

        
        # Api token
        try:
            if 'Authorization token' in config:
                if str(config['Authorization token']) != "":
                    self.token = str(config['Authorization token'])
                    self.persistent_data['token'] = str(config['Authorization token'])
                    if self.DEBUG:
                        print("-Authorization token is present in the config data.")
        except Exception as ex:
            print("Error loading api token from settings: " + str(ex))




    def start_hostapd(self):
        os.system("sudo rfkill unblock wlan")
        time.sleep(1)
        #CHANNEL=`iwlist wlan0 channel | grep Current | sed 's/.*Channel \([0-9]*\).*/\1/g'`
        #echo CHANNEL

        #echo "setting access to internet"
        #sudo cat /proc/sys/net/ipv4/ip_forward
        os.system("sudo bash -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'")
        #sudo sysctl -w net.ipv4.ip_forward=1
        #sudo cat /proc/sys/net/ipv4/ip_forward

        uap_check = run_command_with_lines("ifconfig | grep 'uap0'")
        if 'uap0' in uap_check:
        #if ifconfig | grep -q 'uap0'; then
           print("uap0 was already set up")
           
        else:
        	print("bringing wlan0 down")
        	os.system("sudo ifconfig wlan0 down")

        	time.sleep(1)
        	print("adding uap0 interface")
        	#sudo /sbin/iw dev wlan0 interface add ap@wlan0 type __ap
        	os.system("sudo /sbin/iw phy phy0 interface add uap0 type __ap")
        	#sudo /sbin/iw phy phy0 interface add candle type __ap
        	time.sleep(1)
        	print("setting mac")
        	os.system("sudo ifconfig uap0 hw ether " + str(self.mac_zero))
        	time.sleep(1)
        	print("setting power save settings to off")
        	os.system("sudo iw dev wlan0 set power_save off")
        	os.system("sudo iw dev uap0 set power_save off")
        	time.sleep(1)
        	#sudo ifconfig wlan0 up
        	#sleep 1
        	#sudo ifconfig uap0 up
        	#sleep 1
        	print("setting to up")
        	os.system("sudo ifconfig wlan0 " + str(self.ip_address) + " up")
        	time.sleep(1)
        	os.system("sudo ifconfig uap0 192.168.12.1 up")
        	time.sleep(1)

        	print("adding iptables")
        	#echo ""
        	#echo "BEFORE"
        	#sudo iptables -L
        	#netstat -r
        	os.system("sudo iptables -A INPUT -s 192.168.12.0/24 -j ACCEPT")
        	#sudo iptables -t nat -A POSTROUTING -o wlan0 -s 192.168.12.0/24 ! -d 192.168.12.0/24 -j MASQUERADE
        	#sudo iptables -t nat -A POSTROUTING -j MASQUERADE
        	os.system("sudo iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE")
        	os.system("sudo iptables -A FORWARD -i wlan0 -o uap0 -m state --state RELATED,ESTABLISHED -j ACCEPT")
        	os.system("sudo iptables -A FORWARD -i uap0 -o wlan0 -j ACCEPT")
        	os.system("iptables-save")
        	#echo ""
        	#echo "AFTER"
        	#sudo iptables -L
        	#netstat -r


        	print("starting hostapd")
        	os.system("sudo /usr/sbin/hostapd -B " + self.hostapd_conf_file_path)
        	time.sleep(1)
        



        print("extra up")
        os.system("sudo ifconfig wlan0 up")
        os.system("sudo ifconfig uap0 up")
        sleep(1)
        print("restarting dhcpcd")
        os.system("sudo systemctl restart dhcpcd")
        sleep(1)
        os.system("python3 multicast-relay.py --homebrewNetifaces --interfaces wlan0 uap0")

        print("starting dnsmasq")
        # -K is to add additional hosts file, which could be used as a blocklist for dubious domains
        # -k is keep in foreground
        # -d is no deamon, used for debugging

        #sudo dnsmasq -H ./blocklist-hosts-file.txt -k -d --dns-loop-detect --interface=uap0 --conf-file=./dns_can1.conf
        #sudo dhcpcd --denyinterfaces uap0
        dnsmasq_command = "sudo dnsmasq -k -d --dns-loop-detect --interface=uap0 --conf-file=" + self.dnsmasq_conf_file_path
        #os.system("sudo dnsmasq -k -d --dns-loop-detect --interface=uap0 --conf-file=" + self.dnsmasq_conf_file_path)


        print(str( dnsmasq_command.split() ))

        for path in execute(dnsmasq_command.split()):
            print(".")
            print(path, end="")



 
    def remove_thing(self, device_id):
        try:
            obj = self.get_device(device_id)        
            self.handle_device_removed(obj)                     # Remove hotspot thing from device dictionary
            if self.DEBUG:
                print("User removed Hotspot device")
        except:
            print("Could not remove things from devices")




#
#  PAIRING
#

    def start_pairing(self, timeout):
        """
        Start the pairing process. This starts when the user presses the + button on the things page.
        
        timeout -- Timeout in seconds at which to quit pairing
        """
        if self.pairing:
            #print("-Already pairing")
            return
          
        self.pairing = True
        return
    
    
    
    def cancel_pairing(self):
        """Cancel the pairing process."""
        self.pairing = False
        if self.DEBUG:
            print("End of pairing process. Checking if a new injection is required.")
            
        # Get all the things via the API.
        try:
            self.things = self.api_get("/things")
            #print("Did the things API call")
        except Exception as ex:
            print("Error, couldn't load things at init: " + str(ex))




#
#  UNLOAD
#

    def unload(self):
        print("Shutting down Hotspot. Talk to you soon!")
        
        self.save_persistent_data()
        self.running = False
        



#
#  PERSISTENCE
#

    def save_persistent_data(self):
        if self.DEBUG:
            print("Saving to persistence data store at path: " + str(self.persistence_file_path))
            
        try:
            if not os.path.isfile(self.persistence_file_path):
                open(self.persistence_file_path, 'a').close()
                if self.DEBUG:
                    print("Created an empty persistence file")
            else:
                if self.DEBUG:
                    print("Persistence file existed. Will try to save to it.")

            with open(self.persistence_file_path) as f:
                #if self.DEBUG:
                #    print("saving persistent data: " + str(self.persistent_data))
                json.dump( self.persistent_data, open( self.persistence_file_path, 'w+' ) )
                if self.DEBUG:
                    print("Data stored")
                return True

        except Exception as ex:
            print("Error: could not store data in persistent store: " + str(ex) )
            print(str(self.persistent_data))
            return False




    def update_network_info(self):

        try:
            possible_ip = get_ip()
            if valid_ip(possible_ip):
                self.ip_address = possible_ip
            #if self.DEBUG:
            #    print("My IP address = " + str(self.ip_address))
        except Exception as ex:
            print("Error getting hostname: " + str(ex))

        # Get hostname
        try:
            self.hostname = str(socket.gethostname())
            #if self.DEBUG:
            #    print("fresh hostname = " + str(self.hostname))
        except Exception as ex:
            print("Error getting hostname: " + str(ex) + ", setting hostname to ip_address instead")
            self.hostname = str(self.ip_address)
        
        

def getmac(interface):

  try:
    mac = open('/sys/class/net/'+interface+'/address').readline()
  except:
    mac = "00:00:00:00:00:00"

  return mac[0:17]
  
  
def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line 
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


  
  
  
  