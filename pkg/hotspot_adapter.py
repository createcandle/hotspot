"""Hotspot adapter for Candle Controller."""

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
import re
import json
import time
#import queue
#import signal
import socket
#import asyncio
import logging
import requests
import threading
import selectors
import subprocess
from subprocess import call, Popen
#from collections import namedtuple

    
from gateway_addon import Database, Adapter
from .util import *
from .hotspot_device import *
#from .hotspot_notifier import *

try:
    #from gateway_addon import APIHandler, APIResponse
    from .hotspot_api_handler import *
    #print("HotspotAPIHandler imported")
    #pass
except Exception as ex:
    print("Error, unable to load HotspotAPIHandler: " + str(ex))



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
        #print("Starting Hotspot addon")
        #print(str( os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib') ))
        self.pairing = False
        self.ready = False
        self.running = True
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
        
        self.child_pids = []
        
        self.nmcli_installed = False
        nmcli_check = run_command('which nmcli')
        if nmcli_check != None:
            if str(nmcli_check).startswith('/'):
                self.nmcli_installed = True

        self.hostapd_installed = False
        hostapd_check = run_command('which hostapd')
        if hostapd_check != None:
            if str(hostapd_check).startswith('/'):
                self.hostapd_installed = True
        
        self.previous_dnsmasq_now = ''
        
        self.seconds = 0
        self.allow_launch = True
        self.launched = False
        self.use_without_cable = False
        self.config_skip_network_check = False
        self.cable_needed = False
        self.protected_animals_count = 0 # how many devices are not shown because they are likely a laptop or phone
        
        # blocklists
        self.trackers_update_interval_seconds = 259200 # once every 3 days should be often enough
        
        #print("os.uname() = " + str(os.uname()))

        # Some paths
        #print("self.user_profile:")
        #print(str(self.user_profile))
        self.addon_path = os.path.join(self.user_profile['addonsDir'], self.addon_name)
        #self.dnsmasq_log_path = os.path.join(self.addon_path,"snips","response.wav")
        self.data_dir_path = os.path.join(self.user_profile['dataDir'], self.addon_name)
        self.hostapd_conf_file_path = os.path.join(self.data_dir_path, "hostapd.conf")
        self.dnsmasq_conf_file_path = os.path.join(self.data_dir_path, "dnsmasq.conf")
        self.dnsmasq_log_file_path = os.path.join(self.data_dir_path, "dnsmasq_log.conf")
        self.dnsmasq_leases_file_path = os.path.join(self.data_dir_path, "leases.txt")
        self.dnsmasq_hosts_dir_path = os.path.join(self.data_dir_path, "hosts")
        self.dnsmasq_addon_hosts_dir_path = os.path.join(self.addon_path, "hosts")
        
        self.master_blocklist_file_path = os.path.join(self.dnsmasq_hosts_dir_path, "master_blocklist.txt")
        self.steven_black_blocklist_file_path = os.path.join(self.dnsmasq_hosts_dir_path, "StevenBlack_hosts.txt")
        self.duck_duck_go_blocklist_file_path = os.path.join(self.dnsmasq_hosts_dir_path, "duck_duck_go_blocklist.txt")
        
        
        self.multicast_relay_file_path = os.path.join(self.addon_path, "multicast-relay.py")
        self.time_server_file_path = os.path.join(self.addon_path, "time_server.py")
        
        
        self.is_mac = False
        # Ugly fix for issue with Candle 2.0.2.
        if sys.platform == 'darwin':
            print("RUNNING ON MAC OS")
            self.is_mac = True
            
        self.hostapd_available = False
        hostapd_check = run_command('which hostapd')
        if str(hostapd_check).startswith('/') and str(hostapd_check).endswith('/hostapd'):
            self.hostapd_available = True    
            
        
        self.boot_path = '/boot'
        if os.path.exists('/boot/firmware'):
            self.boot_path = '/boot/firmware'
        
        if os.path.isfile(self.boot_path + "/nohotspot.txt"):
            print("nohotspot.txt file spotted on SD card, so hotspot addon will not launch.")
            return
            
        if os.path.isfile(self.boot_path + "/candle_no_hotspot.txt"):
            print("candle_no_hotspot.txt file spotted on SD card, so hotspot addon will not launch.")
            return
        
        # skip the 90 second wait a bit during development:
        jump45 = os.path.join(self.user_profile['addonsDir'], self.addon_name, "jump45")
        #print("jump45 = " + str(jump45))
        if os.path.isfile(jump45):
            self.seconds = 45
            
        jump70 = os.path.join(self.user_profile['addonsDir'], self.addon_name, "jump70")
        if os.path.isfile(jump70):
            self.seconds = 70
            
        jump88 = os.path.join(self.user_profile['addonsDir'], self.addon_name, "jump88")
        if os.path.isfile(jump88):
            self.seconds = 88


        # Detect the network check override command. if present the hotspot can start even if the device has no network connection, making it fully stand-alone.
        self.skip_network_file_detected = False
        if os.path.isfile(self.boot_path + '/candle_skip_network.txt'):
            self.skip_network_file_detected = True
            #self.seconds = 30 # start the hotspot (90 - 30 =) 60 seconds after the gateway started

        # Make sure the data directory exists
        try:
            if not os.path.isdir(self.data_dir_path):
                os.mkdir( self.data_dir_path )
                print("data directory did not exist, created it now")
        except:
            print("Error: could not make sure data dir exists.")
            
        # Make sure the hosts directory exists
        try:
            if not os.path.isdir(self.dnsmasq_hosts_dir_path):
                os.system("cp -R " + str(self.dnsmasq_addon_hosts_dir_path) + " " + str(self.dnsmasq_hosts_dir_path) )
                #os.mkdir( self.dnsmasq_hosts_dir_path )
                print("hosts directory did not exist, copied the built-in files")
        except:
            print("Error: could not make sure data dir exists.")


        # Get persistent data
        try:
            self.persistence_file_path = os.path.join(self.data_dir_path, 'persistence.json')
            if self.DEBUG:
                print("self.persistence_file_path = " + str(self.persistence_file_path))
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
                        
        except Exception as ex:
            first_run = True
            print("Could not load persistent data (if you just installed the add-on then this is normal): " + str(ex))
            try:
                unique_id = generate_random_string(4)
                self.persistent_data = { 'unique_id':unique_id, 'animals':{}, 'ip_to_mac':{} }
            except Exception as ex:
                print("Error creating initial persistence variable: " + str(ex))
        
        self.mac = get_own_mac("wlan0")
        self.hostname = get_own_hostname()
        if self.DEBUG:
            print("self.hostname = " + str(self.hostname))
        self.mac_zero = self.mac.replace(self.mac[len(self.mac)-1], '0')

        if self.DEBUG:
            print("mac = " + str(self.mac))
            print("mac_zero = " + str(self.mac_zero))
        self.name_server = "87.118.100.175" # German Privacy Foundation
        self.country_code = "NL"
        self.hotspot_name = "Candle"
        self.hotspot_password = "iloveprivacy"
        self.ip_address = None
        
        self.wifi_country_codes_table = {
                    "Algeria":"DZ",
                    "United States":"US",
                    "Canada":"CA",
                    "Japan":"JP",
                    "Germany":"DE",
                    "Netherlands":"NL",
                    "Italy":"IT",
                    "Portugal":"PT",
                    "Luxembourg":"LU",
                    "Norway":"NO",
                    "Finland":"FI",
                    "Denmark":"DK",
                    "Switzerland":"CH",
                    "Czech Republic":"CZ",
                    "Spain":"ES",
                    "United Kingdom":"GB",
                    "South Korea":"KR",
                    "China":"CN",
                    "France":"FR",
                    "Hong Kong":"HK",
                    "Singapore":"SG",
                    "Taiwan":"TW",
                    "Brazil":"BR",
                    "Israel":"IL",
                    "Saudi Arabia":"SA",
                    "Lebanon":"LB",
                    "United Arab Emirates":"AE",
                    "South Africa":"ZA",
                    "Argentina":"AR",
                    "Australia":"AU",
                    "Austria":"AT",
                    "Bolivia":"BO",
                    "Chile":"CL",
                    "Greece":"GR",
                    "Iceland":"IS",
                    "India":"IN",
                    "Ireland":"IE",
                    "Kuwait":"KW",
                    "Liechtenstein":"LI",
                    "Lithuania":"LT",
                    "Mexico":"MX",
                    "Morocco":"MA",
                    "New Zealand":"NZ",
                    "Poland":"PL",
                    "Puerto Rico":"PR",
                    "Slovak Republic":"SK",
                    "Slovenia":"SI",
                    "Thailand":"TH",
                    "Uruguay":"UY",
                    "Panama":"PA",
                    "Russia":"RU",
                    "Egypt":"EG",
                    "Trinidad and Tobago":"TT",
                    "Turkey":"TR",
                    "Costa Rica":"CR",
                    "Ecuador":"EC",
                    "Honduras":"HN",
                    "Kenya":"KE",
                    "Ukraine":"UA",
                    "Vietnam":"VN",
                    "Bulgaria":"BG",
                    "Cyprus":"CY",
                    "Estonia":"EE",
                    "Mauritius":"MU",
                    "Romania":"RO",
                    "Serbia and Montenegro":"CS",
                    "Indonesia":"ID",
                    "Peru":"PE",
                    "Venezuela":"VE",
                    "Jamaica":"JM",
                    "Bahrain":"BH",
                    "Oman":"OM",
                    "Jordan":"JO",
                    "Bermuda":"BM",
                    "Colombia":"CO",
                    "Dominican Republic":"DO",
                    "Guatemala":"GT",
                    "Philippines":"PH",
                    "Sri Lanka":"LK",
                    "El Salvador":"SV",
                    "Tunisia":"TN",
                    "Pakistan":"PK",
                    "Qatar":"QA"
                    }
        
        
        
        #Time server
        self.time_server = True
        
        # hostapd
        self.hostapd_pid = None
        
        # dnsmasq
        self.dnsmasq_pid = None
        self.dnsmasq_data = ""
        self.use_blocklists = True
        
        self.use_multicast_relay = False
        
        self.ethernet_connected = self.ethernet_check()
        
        self.last_new_domain_countdown = 0
        self.last_any_domain_countdown = 0
        self.last_blocked_domain_countdown = 0
        self.domain_countdown_time = 5
        
        # tracking blocklist
        self.updating_blocklists_allowed = False
        
        # TODO DEV
        #os.system("sudo pkill dnsmasq")
        
        
        
        try:
            if 'unique_id' not in self.persistent_data: # to remember what the main hotspot server is, for satellites.
                print("unique_id was not in persistent data, adding it now.")
                self.persistent_data['unique_id'] = generate_random_string(4)
            if 'master_blocklist' not in self.persistent_data:
                print("master_blocklist was not in persistent data, adding it now.")
                self.persistent_data['master_blocklist'] = []
            if 'animals' not in self.persistent_data:
                print("animals was not in persistent data, adding it now.")
                self.persistent_data['animals'] = {}
            if 'ip_to_mac' not in self.persistent_data:
                print("ip_to_mac was not in persistent data, adding it now.")
                self.persistent_data['ip_to_mac'] = {}
            
            if 'last_trackers_update_time' not in self.persistent_data:
                print("last_trackers_update_time was not in persistent data, adding it now.")
                self.persistent_data['last_trackers_update_time'] = 0
            
                
        except Exception as ex:
            print("Error fixing missing values in persistent data: " + str(ex))
        
        
        #
        # Create UI
        #
        # Even if the user doesn't want to see a UI, it may be the case that the HTML is still loaded somewhere. So the API should be available regardless.
        
        try:
            self.api_handler = HotspotAPIHandler(self, verbose=True)
            #self.manager_proxy.add_api_handler(self.api_handler)
            if self.DEBUG:
                print("Extension API handler initiated")
        except Exception as e:
            print("Failed to start API handler (this only works on gateway version 0.10 or higher). Error: " + str(e))
            
        
        # LOAD CONFIG
        try:
            self.add_from_config()
        except Exception as ex:
            print("Error loading config: " + str(ex))
            
        self.ssid = self.hotspot_name + " " + self.persistent_data['unique_id'] + "_nomap"
        if self.DEBUG:
            print("ssid = " + str(self.ssid))
        
        if self.nmcli_installed == False:
            time.sleep(3) # give the network some more time to settle
        
        filename = "/etc/resolv.conf"
        with open(filename) as f:
            content = f.readlines()

        for line in content:
            #print(line)
            if line.startswith( "nameserver " ):
                self.name_server = line.split(" ")[1]
                self.name_server = self.name_server.replace("\n","")
                if self.DEBUG:
                    print("name server from /etc/resolv.conf: " + str(self.name_server))
            

        #if self.DEBUG:
        #    print("self.persistent_data is now:")
        #    print(str(self.persistent_data))

 
        # Connected via ethernet?
        
        if os.path.exists('/sys/class/net/eth0/operstate'):
            eth0_operstate = run_command('cat /sys/class/net/eth0/operstate')
            if str(eth0_operstate).strip() == 'down':
                if self.DEBUG:
                    print("No ethernet cable connected")
                self.cable_needed = True    
            
        
        #if self.DEBUG:
        #    print("ethernet_state: " + str(self.ethernet_state))
        #if 'down' in str(self.ethernet_state) and self.use_without_cable == False:
        #    if self.DEBUG:
        #        print("No ethernet, and Hotspot may not run without an ethernet connection. Stopping.")
        #    self.cable_needed = True    


        # If the file was detected, and if the configuration says to skip,
        if self.skip_network_file_detected:
            self.cable_needed = False

        
        #time.sleep(1)


        # Create device
        try:
            hotspot_device = HotspotDevice(self)
            self.handle_device_added(hotspot_device)
            if self.DEBUG:
                print("Hotspot thing created")
        except Exception as ex:
            print("Could not create hotspot device:" + str(ex))


        
        
        
        
        # starting time server
        
        hostapd_command = "sudo /usr/sbin/hostapd -B " + self.hostapd_conf_file_path
        time_server_command = "sudo python3 " + self.time_server_file_path + " 192.168.12.1 123"

        if self.nmcli_installed == False and self.hostapd_installed == True:
            kill(time_server_command)
            if self.time_server:
                if self.DEBUG:
                    print("starting time server. Command: " + str(time_server_command))
                self.time_server_process = subprocess.Popen(time_server_command.split(), stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, universal_newlines=True, preexec_fn=os.setpgrp)
                if self.DEBUG:
                    print("time server PID = " + str(self.time_server_process.pid))
                self.time_server_pid = self.time_server_process.pid
                self.child_pids.append(self.time_server_process.pid)
                if self.DEBUG:
                    print("internal time server started")
        


        # Start the internal clock which is used to handle timers. It also receives messages from the notifier.
        if self.DEBUG:
            print("Starting the internal clock")
        try:
            self.t = threading.Thread(target=self.clock)
            self.t.daemon = True
            self.t.start()
            pass
        except:
            print("Error starting the clock thread")


            
        #time.sleep(1.34)
        
        # Set thing to connected state
        try:
            #self.devices['hotspot'].connected = True
            #self.devices['hotspot'].connected_notify(True)
            pass
        except Exception as ex:
            print("Error setting device details: " + str(ex))
            
        #time.sleep(5.4) # Snips needs some time to start


        #time.sleep(10)
        
        self.save_persistent_data()
        if self.DEBUG:
            print("end of init")

            
        self.ready = True
        
        # Only continue if there is an ethernet cable plugged in (unless the user has overridden this)
        if self.cable_needed:
            return

        #if self.allow_launch:
            #if self.DEBUG:
            #    print("disabling wifi power saving")
            #os.system("sudo iw dev wlan0 set power_save off")

        if self.nmcli_installed == False and self.hostapd_installed == True:
            while self.running:
                time.sleep(1)
                if self.allow_launch:
                    self.seconds += 1
                try:
                    if self.seconds < 91:
                        if self.DEBUG:
                            print("hotspot start countdown: ", 90 - self.seconds)
                    if self.allow_launch == True:
                        if self.seconds == 90:
                            if self.allow_launch == True:
                                if self.DEBUG:
                                    print("CLOCK -> 90sec -> start hotspot")
                                self.start_hostapd() # it stops here, as this is blocking
                            
                                #self.d = threading.Thread(target=self.start_hostapd)
                                #self.d.daemon = True
                                #self.d.start()

                except Exception as ex:
                    if self.DEBUG:
                        print("Error in dnsmasq loop: " + str(ex))
                

                
                
            
    def clock(self):
        if self.DEBUG:
            print("in clock thread")
            
        unblock_countdown = 30
        while self.running:
            time.sleep(1)
            
            #self.previous_dnsmasq_now
            
            dnsmasq_now_lines = []
            if os.path.exists('/home/pi/dnsmasq_now.txt'):
                with open('/home/pi/dnsmasq_now.txt') as dnsmasq_now_f:
                    dnsmasq_now_lines = dnsmasq_now_f.readlines()
                os.remove('/home/pi/dnsmasq_now.txt')
            
            
            self.devices['hotspot'].properties['activity'].update(len(dnsmasq_now_lines))
            
            if len(dnsmasq_now_lines):
                for line in dnsmasq_now_lines:
                    self.parse_dnsmasq(line)
            
            #print("self.last_any_domain_countdown = " + str(self.last_any_domain_countdown))
            if self.last_new_domain_countdown > 0:
                self.last_new_domain_countdown -= 1
                if self.last_new_domain_countdown == 0:
                    self.devices['hotspot'].properties['new'].update(False)
                
            if self.last_any_domain_countdown > 0:
                self.last_any_domain_countdown -= 1
                if self.last_any_domain_countdown == 0:
                    self.devices['hotspot'].properties['any'].update(False)
                
            if self.last_blocked_domain_countdown > 0:
                self.last_blocked_domain_countdown -= 1
                if self.last_blocked_domain_countdown == 0:
                    self.devices['hotspot'].properties['blocked'].update(False)
            
            #if self.DEBUG:
            #    print("unblock_countdown: " + str(unblock_countdown))
                
            unblock_countdown -= 1
            if unblock_countdown < 1:
                unblock_countdown = 30
                if self.nmcli_installed == False and self.hostapd_installed == True:
                    os.system('sudo pkill wpa_supplicant')
                # it's strange that this is needed.. but it works. Thanks to https://github.com/RaspAP/raspap-webgui/issues/200
                
                #/usr/sbin/rfkill list wifi | grep -q "Soft blocked: yes"
                #wifi_block_result = shell('/usr/sbin/rfkill list wifi')
                #if self.DEBUG:
                #    print("wifi_block_result: " + str(wifi_block_result))
                #if "Soft blocked: yes" in wifi_block_result:
                #if self.DEBUG:
                #    print('periodic wifi unblocking')
                #os.system('/usr/sbin/rfkill block wifi;/usr/sbin/rfkill unblock wifi')
                #os.system('/usr/sbin/rfkill unblock wifi')
                    
                if self.updating_blocklists_allowed == True:
                    if time.time() - self.trackers_update_interval_seconds > self.persistent_data['last_trackers_update_time']:
                        self.update_blocklists()
                    
                    
                    
        if self.DEBUG:
            print("hotspot clock stopped")         
                
                
                
#
#  GET CONFIG
#

    # Read the settings from the add-on settings page
    def add_from_config(self):
        """Attempt to add all configured devices."""
        
        store_updated_settings = False
        
        try:
            database = Database('hotspot')
            if not database.open():
                print("Could not open settings database")
                #self.close_proxy()
                return
            
            config = database.load_config()
            database.close()
            
        except:
            print("Error! Failed to open settings database.")
            #self.close_proxy()
            return
        
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
        except Exception as ex:
            print("Error! Failed to store overridden settings in database: " + str(ex))
        
        
        
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
            print("Error loading password from config: " + str(ex))

        # Country code
        try:
            if 'Country' in config:
                if self.DEBUG:
                    print("-Country is present in the config data: " + str(config['Country']))
                if str(config['Country']) in self.wifi_country_codes_table:
                    self.country_code = self.wifi_country_codes_table[ str(config['Country']) ]
                else:
                    if self.DEBUG:
                        print("-ERROR, Country not in Wi-Fi code lookup list")
        except Exception as ex:
            print("Error loading country from config: " + str(ex))

        if 'Use without a network cable' in config:
            self.use_without_cable = bool(config['Use without a network cable']) 
            if self.DEBUG:
                print("-Use without a network cable preference was in config, and is now set to: " + str(self.use_without_cable))

        if 'Use blocklist' in config:
            self.use_blocklists = bool(config['Use blocklist']) 
            if self.DEBUG:
                print("-Blocklist preference was in config, and is now set to: " + str(self.use_blocklists))
        
        if 'Allow blocklist updating' in config:
            self.updating_blocklists_allowed = bool(config['Allow blocklist updating']) 
            if self.DEBUG:
                print("-Blocklist updating preference was in config, and is now set to: " + str(self.updating_blocklists_allowed))
        
        if 'Multicast relay' in config:
            self.use_multicast_relay = bool(config['Multicast relay']) 
            if self.DEBUG:
                print("-Multicast relay preference was in config, and is now set to: " + str(self.use_multicast_relay))
        
        
        if 'Time server' in config:
            self.time_server = bool(config['Time server']) 
            if self.DEBUG:
                print("-Time server preference was in config, and is now set to: " + str(self.time_server))
                
        
        if 'Skip network check' in config:
            self.config_skip_network_check = bool(config['Skip network check']) 
            if self.config_skip_network_check == False:
                if os.path.isfile(self.boot_path + '/candle_skip_network.txt'):
                    if self.DEBUG:
                        print("removing candle_skip_network.txt from boot partition")
                    os.system('sudo rm ' + self.boot_path + '/candle_skip_network.txt')
                self.skip_network_file_detected = False
            else:
                if self.DEBUG:
                    print("creating candle_skip_network.txt")
                os.system('sudo touch ' + self.boot_path + '/candle_skip_network.txt')
                #self.skip_network_file_detected = True
		
		
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
  
        # get/update network info
        try:
            self.update_network_info()
            self.previous_hostname = self.hostname
        except Exception as ex:
            if self.DEBUG:
                print("Error getting ip address: " + str(ex)) 
        
        if self.nmcli_installed == True:
            if self.DEBUG:
                print("hotspot addon will not start hostapd, as nmcli is installed")
            return
        
        if self.ip_address == None:
            if self.DEBUG:
                print("Error, no valid IP address. Will not start hotspot (hostapd)")
            return
        
        if self.is_mac:
            if self.DEBUG:
                print("aborting start_hostapd on Mac OS")
            return
        
        if self.hostapd_available == False:
            if self.DEBUG:
                print("aborting start_hostapd as hostapd does not seem to be installed")
            return
        
        self.send_pairing_prompt( "Creating Hotspot" )
        

        #
        # DNSMASQ CONF
        #

        #dnsmasq_conf_string = """interface=lo,uap0
        dnsmasq_conf_string = """interface=lo,uap0
no-dhcp-interface=lo,wlan0,eth0
# gives out IP adddresses predictably, starting with x, then x+1, then x+2, etc.
#strict-order 

# experiment
enable-ra
#dhcp-option=19,0           # option ip-forwarding off
# This alias makes a result of 1.2.3.4 appear as 5.6.7.8
#alias=1.2.3.4,5.6.7.8
# and this maps 1.2.3.x to 5.6.7.x
#alias=1.2.3.0,5.6.7.0,255.255.255.0
# and this maps 192.168.0.10->192.168.0.40 to 10.0.0.10->10.0.0.40
#alias=192.168.0.10-192.168.0.40,10.0.0.0,255.255.255.0
# fc00::/7
dhcp-option=option6:dns-server,[::]
#dhcp-range=2001:db8:2:300:1234:5678:abcd:100,2001:db8:2:300:1234:5678:abcd:400,ra-only,infinite

dhcp-authoritative
dhcp-rapid-commit
bind-interfaces
#bind-dynamic
server=""" + self.name_server + "\n"

        dnsmasq_conf_string += """domain-needed
#domain=uap
#rebind_protection=0
dns-loop-detect
domain=local
#local=/local/ 

# prevent packets with malformed domain names and packets with private IP addresses from leaving the network
# Never forward plain names (without a dot or domain part)
domain-needed
# Never forward addresses in the non-routed address spaces.
bogus-priv


#local-service
cache-size=1500
no-negcache
dhcp-client-update
dhcp-range=192.168.12.2,192.168.12.30,255.255.255.0,1h
#dhcp-option=option:gateway,192.168.12.1
dhcp-option=option:router,192.168.12.1
#dhcp-option=option6:dns-server,[]
dhcp-option=option:dns-server,192.168.12.1,""" + self.name_server + "\n"

#dhcp-option=option:dns-server,192.168.12.1,""" + self.name_server + "\n"

#dhcp-option=option:dns-server,192.168.12.1,8.8.8.8,""" + self.name_server + "\n"

        #dnsmasq_conf_string += "\n"
        dnsmasq_conf_string += """#dhcp-option=option:dns-server,192.168.12.1,192.168.2.2,8.8.8.8
dhcp-option=option:ip-forward-enable,1
dhcp-lease-max=50
dhcp-leasefile=""" + self.dnsmasq_leases_file_path + "\n"

        dnsmasq_conf_string += """#listen-address=192.168.12.1
log-queries
log-dhcp
log-facility=-
""" # use /dev/null ?

        if self.time_server:
            dnsmasq_conf_string += "dhcp-option=option:ntp-server,192.168.12.1\n"

#log-facility=/tmp/candle_dnsmasq.log\n

        #dnsmasq_conf_string += "address=/" + self.hostname + ".local/192.168.12.1\n"
        #dnsmasq_conf_string += "address=/privacylabel.org/192.168.12.1\n"

        if self.DEBUG:
            print("")
            print("___dnsmasq_conf_string___")
            print(str(dnsmasq_conf_string))
        textfile = open(self.dnsmasq_conf_file_path, "w")
        a = textfile.write(dnsmasq_conf_string)
        textfile.close()

        
        
        
        #
        # HOSTAPD CONF
        #
        
        hostapd_conf_string = """interface=uap0
driver=nl80211
#logger_syslog_level=0
bssid=""" + self.mac_zero + "\n"
        
        hostapd_conf_string += "ssid=" + self.ssid + "\n"
        #dnsmasq_conf_string += "#channel=" + self.wifi_channel # not necessary, will always be the same as the wifi
        hostapd_conf_string += "country_code=" + self.country_code + "\n"
        
        hostapd_conf_string += """hw_mode=g
#channel=1
channel=6
ieee80211n=1
wmm_enabled=1
auth_algs=1
wpa=2
wpa_passphrase=""" + self.hotspot_password + "\n"

        hostapd_conf_string += """wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP"""

        # TODO - this may provide a hostAPD CLI. Could be useful to disable it on unload?
        # E.G. you can then use 'sudo hostapd_cli disable'
        #ctrl_interface=/var/run/hostapd
        #ctrl_interface_group=0
        


        if self.DEBUG:
            print("")
            print("___hostapd_conf_string___")
            print(str(hostapd_conf_string))
        textfile = open(self.hostapd_conf_file_path, "w")
        a = textfile.write(hostapd_conf_string)
        textfile.close()
        
        #os.system("sudo echo 'hotspot' >> /var/log/syslog")
        
        #os.system("sudo rfkill unblock wlan")
        os.system("sudo rfkill unblock 0")
        time.sleep(1)
        #CHANNEL=`iwlist wlan0 channel | grep Current | sed 's/.*Channel \([0-9]*\).*/\1/g'`
        #echo CHANNEL

        # enabling ip forwarding between interfaces within the pi itself
        os.system("sudo sysctl -w net.ipv4.ip_forward=1")
        os.system("sudo sysctl -w net.ipv6.ip_forward=1")
        #net/ipv6/conf/all/forwarding=1
        #os.system("sudo sysctl -w net.ipv4.conf.uap0.route_localnet=1")
        time.sleep(.1)
        
              
        try:
            
            # kill any potential left-overs
            #kill("multicast-relay.py")
            #kill("wpa_supplicant -B -c/etc/wpa_supplicant/wpa_supplicant.conf -iuap0")
            os.system("sudo pkill hostapd")
            
            # check if uap0 has already been created (e.g. is the addon is restarted)  
            uap_check = shell("ifconfig | grep 'uap0'")
            if 'uap0' in uap_check:
                if self.DEBUG:
                    print("Error: uap0 was already set up?")
                if not self.ethernet_connected:
                    if self.DEBUG:
                        print("restarting the hotspot addon is only supported if a network cable is attached. To restart the hotspot, please reboot the entire controller.")
                    return
                else:
                    os.system("sudo iw dev uap0 del")
                    time.sleep(2)
            
			
            # ifconfig explanation:
            #http://litux.nl/Reference/books/7213/ddu0293.html
        
            # dhcpcd needs to be (temporarily) down when the new interface is created, otherwise it will start wpa_supplicant for it, and that will create errors.
            if self.DEBUG:
                print("stopping dhcpcd")
            os.system("sudo systemctl stop dhcpcd.service")
            time.sleep(.5)
            os.system("sudo pkill dhcpcd")
            os.system("sudo systemctl stop wpa_supplicant.service")
            kill("wpa_supplicant -B -c/etc/wpa_supplicant/wpa_supplicant.conf -iuap0")
            os.system("sudo pkill wpa_supplicant")
            os.system("sudo wpa_cli terminate")
            kill("/sbin/wpa_supplicant -u -s -O /run/wpa_supplicant")
            #os.system("sudo pkill wpa_supplicant")
            time.sleep(.1)
            #os.system("sudo rfkill unblock 0")
            os.system("sudo rfkill unblock wifi")
            
            
            #os.system("sudo dhcpcd --denyinterfaces uap0 --nohook wpa_supplicant")
            #time.sleep(2)
            if self.DEBUG:
                print("adding uap0 interface")
            os.system("sudo /sbin/iw phy phy0 interface add uap0 type __ap")
            
        	#sudo /sbin/iw phy phy0 interface add candle type __ap
            time.sleep(.1)
            if self.DEBUG:
                print("setting mac")
            os.system("sudo ifconfig uap0 hw ether " + str(self.mac_zero))
            time.sleep(.1)
            if self.DEBUG:
                print("setting power save settings to off")
            #os.system("sudo iw dev wlan0 set power_save off")
            os.system("sudo ip link set dev wlan0 down") # https://raspberrypi.stackexchange.com/questions/85599/how-to-start-stop-wpa-supplicant-on-default-raspbian
            os.system("sudo iw dev uap0 set power_save off")

            if self.DEBUG:
                print("adding iptables")
                print("replacing old broad gateway iptables rules with more precise ip-based ones")
                print("- removing 2 mangle rules")
            #os.system("sudo iptables -t mangle --flush")
            #os.system("sudo iptables -t nat --flush")
    
            os.system("sudo iptables -t mangle -D PREROUTING -p tcp --dport 80 -j MARK --set-mark 1")
            os.system("sudo iptables -t mangle -D PREROUTING -p tcp --dport 443 -j MARK --set-mark 1")
         
    
            if self.DEBUG:
                print("- removing 2 'mark 0x1' input rules")
            os.system("sudo iptables -D INPUT -p tcp -m state --state NEW -m tcp --dport 8080 -m mark --mark 0x1 -j ACCEPT")
            os.system("sudo iptables -D INPUT -p tcp -m state --state NEW -m tcp --dport 4443 -m mark --mark 0x1 -j ACCEPT")
        
            if self.DEBUG:
                print("- removing 2 port changing prerouting rules")
            os.system("sudo iptables -t nat -D PREROUTING -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 8080")
            os.system("sudo iptables -t nat -D PREROUTING -p tcp -m tcp --dport 443 -j REDIRECT --to-ports 4443")
            #os.system("sudo iptables -t mangle -A PREROUTING -p tcp --dport 80 -d 192.168.12.1 -j MARK --set-mark 1")
            #os.system("sudo iptables -t mangle -A PREROUTING -p tcp --dport 443 -d 192.168.12.1 -j MARK --set-mark 1")
            #os.system("sudo iptables -t mangle -A PREROUTING -p tcp --dport 80 -d " + str(self.ip_address) + " -j MARK --set-mark 1")
            #os.system("sudo iptables -t mangle -A PREROUTING -p tcp --dport 443 -d " + str(self.ip_address) + " -j MARK --set-mark 1")
    
    
            # forward incoming requests to ports 80 and 433 from the wlan side to the gateway UI
            #os.system("iptables -t mangle -A PREROUTING -p tcp --dport 80 -d " + str(self.ip_address) + " -j MARK --set-mark 1")
            #os.system("iptables -t mangle -A PREROUTING -p tcp --dport 4443 -d " + str(self.ip_address) + " -j MARK --set-mark 1")
        

        
            iptables_nat = shell("sudo iptables -t nat -S")
            if self.DEBUG:
                print("----- IP TABLES ----")
                print(iptables_nat)
                print("----- - ---- - -- --")
            if "-A PREROUTING -p tcp --dport 80 -d 192.168.12.1 -j REDIRECT --to-port 8080" not in iptables_nat:
        
                # shift internal ip address of gateway to port 8080 and 4443
                if self.DEBUG:
                    print("- addding ip-based port redirect for internal ip")
                os.system("sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -d 192.168.12.1 -j REDIRECT --to-port 8080")
                os.system("sudo iptables -t nat -A PREROUTING -p tcp --dport 443 -d 192.168.12.1 -j REDIRECT --to-port 4443")
    
                # shift external ip address of gateway to ports 8080 and 4443
                if self.DEBUG:
                    print("- addding ip-based port redirect for external ip")
                os.system("sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -d " + str(self.ip_address) + " -j REDIRECT --to-port 8080")
                os.system("sudo iptables -t nat -A PREROUTING -p tcp --dport 443 -d " + str(self.ip_address) + " -j REDIRECT --to-port 4443")
    
                # sudo iptables -t mangle -A PREROUTING -p tcp --dport 80 -d 192.168.2.165 -j MARK --set-mark 1
                if self.DEBUG:
                    print("finished replacing iptables to ports 8080 and 4443")
    
    
                if self.DEBUG:
                    print("- addding uap0 <-> wlan0/eth0 traversal")
                os.system("sudo iptables -A FORWARD -d 192.168.12.0/24 -o uap0 -j ACCEPT")
                os.system("sudo ip6tables -A FORWARD -d ff02::1 -o uap0 -j ACCEPT")
                

                if self.DEBUG:
                    print("- addding NAT")
                os.system("sudo iptables -t nat -A POSTROUTING -s 192.168.12.0/24 ! -d 192.168.12.0/24  -j MASQUERADE")
                os.system("sudo ip6tables -t nat -A POSTROUTING -s ff02::1 ! -d ff02::1  -j MASQUERADE")
                #os.system("sudo ip6tables -t nat -A POSTROUTING -s fd00::1 ! -d fd00::1  -j MASQUERADE")
                
                
                # drop DHCP requests to get an IPV6 address.
                os.system("sudo ip6tables -A INPUT -m state --state NEW -m udp -p udp -s fe80::/10 --dport 546 -j DROP")
                
                # THIS
                #os.system("sudo iptables -A FORWARD -i wlan0 -o uap0 -m state --state RELATED,ESTABLISHED -j ACCEPT")
                os.system("sudo iptables -A FORWARD -i eth0 -o uap0 -j ACCEPT")
                os.system("sudo iptables -A FORWARD -i uap0 -o eth0 -j ACCEPT")
                
                os.system("sudo iptables -A FORWARD -i wlan0 -o uap0 -j ACCEPT")
                
                #os.system("sudo iptables -A FORWARD -i uap0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT")
                os.system("sudo iptables -A FORWARD -i uap0 -o wlan0 -j ACCEPT")
                
                
                os.system("sudo ip6tables -A FORWARD -i eth0 -o uap0 -j ACCEPT")
                os.system("sudo ip6tables -A FORWARD -i uap0 -o eth0 -j ACCEPT")
                
                os.system("sudo ip6tables -A FORWARD -i wlan0 -o uap0 -j ACCEPT")
                
                #os.system("sudo iptables -A FORWARD -i uap0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT")
                os.system("sudo ip6tables -A FORWARD -i uap0 -o wlan0 -j ACCEPT")
                
                # add ETH0 support?

                
                # allow ping explicitly, from inside to outside
                #os.system("iptables -A OUTPUT -p icmp --icmp-type echo-request -j ACCEPT")
                #os.system("iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT")
                #os.system("sudo iptables -A OUTPUT -p icmp -j ACCEPT")
                #os.system("sudo iptables -A INPUT -p icmp -j ACCEPT")
                
                # allow everything on localhost
                #os.system("sudo iptables -A INPUT -i lo -j ACCEPT")
                #os.system("sudo iptables -A OUTPUT -o lo -j ACCEPT")
                
                
                
    
    
                # from: https://superuser.com/questions/684275/how-to-forward-packets-between-two-interfaces
    
                
                #os.system("sudo iptables -A FORWARD -d 192.168.2.2 -i uap0 -p udp --dport 53 -m iprange --src-range 192.168.12.2-192.168.12.255 -j ACCEPT")
                #os.system("sudo iptables -A FORWARD -d 192.168.12.1 -i uap0 -p udp --dport 53 -m iprange --src-range 192.168.12.2-192.168.12.255 -j ACCEPT")
                
                os.system("sudo iptables -t nat -A PREROUTING -i uap0 -p udp --dport 53 -j DNAT --to-destination 192.168.12.1:53")
                
                
                if not self.name_server.startswith("192.168.12"):
                    if self.DEBUG:
                        print("blocking access to gateway UI from uap0 network")
                    #os.system("sudo iptables -A FORWARD -d 192.168.2.2 -i uap0 -p udp --dport 53 -m iprange --src-range 192.168.12.2-192.168.12.255 -j ACCEPT")
                    #os.system("sudo iptables -A FORWARD -d 192.168.2.2  -p tcp -m tcp --dport 80 -j DROP")
                    #os.system("sudo iptables -A FORWARD -d 192.168.2.2  -p tcp -m tcp --dport 443 -j DROP")
                    #os.system("sudo iptables -A FORWARD -d 192.168.2.2 -m iprange --src-range 192.168.12.2-192.168.12.255 -j DROP")
                    
                    #sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j DNAT --to-destination 192.0.2.2
                    
                    #sudo iptables -t nat -A PREROUTING -i uap0 -p udp --dport 123 -j DNAT --to-destination 192.0.2.2
                    #iptables -t nat -A OUTPUT -p udp --dport 123 -j DNAT --to-destination 192.168.12.1:1620
                    
                    # Route NTP requests to the local server
                    
                    
                    
                    
                    #os.system("sudo iptables -A FORWARD -i uap0 -d 192.168.2.2 -j DROP")
                if self.time_server:
                    if self.DEBUG:
                        print("routing to local NTP time server")
                    os.system("sudo iptables -t nat -A PREROUTING -i uap0 -p udp --dport 123 -j DNAT --to-destination 192.168.12.1:123")
                    
                #os.system("iptables -A OUTPUT -p icmp --icmp-type echo-request -j DROP")
    
                # https://linuxnatives.net/2014/create-wireless-access-point-hostapd
    
                #os.system("sudo iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT")
    
    
                # The origina; iptables from the Gateway
                #iptables -t mangle -A PREROUTING -p tcp --dport 80 -j MARK --set-mark 1
                #iptables -t mangle -A PREROUTING -p tcp --dport 443 -j MARK --set-mark 1
    
                #iptables -t mangle -A PREROUTING -p tcp --dport 80 -j MARK --set-mark 1
                #iptables -t mangle -A PREROUTING -p tcp --dport 443 -j MARK --set-mark 1
    
            
            
            else:
                if self.DEBUG:
                    print("NOT ADDING EXTRA IPTABLES RULES (ALREADY EXISTED?)")
            
            #print("bringing uap0 up")
            #os.system("sudo ifconfig uap0 up") # simpler
            #time.sleep(2)
            if self.DEBUG:
                print(str(shell("ifconfig")))


            if self.DEBUG:
                print("adding ip addresses to uap0 interface")
            
            # once the interface gains an IP, avahi will spring into action.
            os.system("sudo ifconfig uap0 192.168.12.1 netmask 255.255.255.0 broadcast 192.168.12.255") # simpler
            time.sleep(.1)
            kill("wpa_supplicant -B -c/etc/wpa_supplicant/wpa_supplicant.conf -iuap0")
            
            if self.DEBUG:
                print("__")
                print("HOSTAPD COMMAND")
            hostapd_command = "sudo /usr/sbin/hostapd -B " + self.hostapd_conf_file_path
            if self.DEBUG:
                print(str( hostapd_command ))
            
            kill(hostapd_command)
        
            if self.DEBUG:
                print("starting hostapd")
            self.hostapd_process = subprocess.Popen(hostapd_command.split(), stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE, universal_newlines=True, preexec_fn=os.setpgrp)
            if self.DEBUG:
                print("hostapd PID = " + str(self.hostapd_process.pid))
            self.hostapd_pid = self.hostapd_process.pid
            self.child_pids.append(self.hostapd_process.pid)
        
        
            dhcp_check = ""
            
            dhcp_check = shell("sudo /sbin/dhcpcd -w --denyinterfaces uap0")
            print(str(dhcp_check))
            if dhcp_check == "":
                if self.DEBUG:
                    print("starting dhcpcd with denyinterfaces for uap0")
                #print("removing old dhcpcd with denyinterfaces already in place")
                #kill("sudo /sbin/dhcpcd -w --denyinterfaces uap0")
                #time.sleep(1)
                os.system("sudo /sbin/dhcpcd -w --denyinterfaces uap0") # --nohook wpa_supplicant")
            
            time.sleep(3)
            
            
            # dhcpsd restarts wpa_supplicant.. so it must be stopped again
            kill("wpa_supplicant -B -c/etc/wpa_supplicant/wpa_supplicant.conf -iuap0")
            
            if self.use_multicast_relay:
                print("starting multicast relay")
                kill("multicast-relay.py")
                time.sleep(1)
                os.system("python3 multicast-relay.py --homebrewNetifaces --ifNameStructLen 32 --interfaces wlan0 uap0 &")
            
            """
            if self.use_multicast_relay:
                if self.DEBUG:
                    print("starting multicast relay")
                os.system("python3 " + self.multicast_relay_file_path + " --interfaces wlan0 uap0")
            else:
                if self.DEBUG:
                    print("NOT starting multicast relay")
            """
            
            kill("ps ax | grep 'sudo dnsmasq -k -d --interface=uap0'")
            
            if self.DEBUG:
                print("starting dnsmasq")
    
            hosts_part = ""
            if self.use_blocklists:
                hosts_part = " --hostsdir=" + self.dnsmasq_hosts_dir_path
 
            dnsmasq_command = "sudo dnsmasq -k -d --interface=uap0 --no-daemon --log-async --conf-file=" + str(self.dnsmasq_conf_file_path) + hosts_part #  --no-hosts
            # sudo dnsmasq -k -d --interface=uap0 --no-daemon --log-async --conf-file=/home/pi/.webthings/data/hotspot/dnsmasq.conf --hostsdir=/home/pi/.webthings/data/hotspot/hosts


            self.launched = True

            while self.running:
                if self.DEBUG:
                    print("__")
                    print("DNSMASQ COMMAND")
                    print(str( dnsmasq_command ))
                self.dnsmasq_process = subprocess.Popen(dnsmasq_command.split(), stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE, universal_newlines=True, preexec_fn=os.setpgrp)
                if self.DEBUG:
                    print("dnsmasq PID = " + str(self.dnsmasq_process.pid))
                self.dnsmasq_pid = self.dnsmasq_process.pid
                self.child_pids.append( self.dnsmasq_process.pid )

                # Read both stdout and stderr simultaneously
                sel = selectors.DefaultSelector()
                sel.register(self.dnsmasq_process.stdout, selectors.EVENT_READ)
                sel.register(self.dnsmasq_process.stderr, selectors.EVENT_READ)
                
                while self.running:
                    for key, val1 in sel.select():
                        line = key.fileobj.readline()
                        if not line:
                            if self.DEBUG:
                                print("dnsmasq loop: ok was false")
                            ok = False # still used?
                            break
                        if key.fileobj is self.dnsmasq_process.stdout:
                            #if self.DEBUG:
                            #print(f"STDOUT: {line}", end="", file=sys.stdout)
                            self.parse_dnsmasq(f"{line}")
                        else:
                            #print(f"STDERR: {line}", end="", file=sys.stderr)
                            self.parse_dnsmasq(f"{line}")
                    time.sleep(.02)
                        
                        
            if self.DEBUG:
                print("BEYOND STARTING DNSMASQ")
            #print(str(shell("ifconfig")))
            
            #print("bringing uap0 up")
            #os.system("sudo ifconfig uap0 up")
            
            #print("killing wpa_supplicant")
            #kill("wpa_supplicant -B -c/etc/wpa_supplicant/wpa_supplicant.conf -iuap0")
            #time.sleep(2)
            #kill("wpa_supplicant -B -c/etc/wpa_supplicant/wpa_supplicant.conf -iuap0")
            #kill_uap0_wpa()
            
            

            #python3 multicast-relay.py --interfaces wlan0 uap0
            
                    

        except Exception as ex:
            print("Error starting hotspot network: " + str(ex))
            
            



    def parse_dnsmasq(self,line):
        line = line.replace("\n", "")
        if self.DEBUG:
            print("parse_dnsmasq: parsing: --" + str(line) + "--")
        
        if len(line) < 2:
            if self.DEBUG:
                print("- parse_dnsmasq: skipping empty line")
            return    
            
        if "available DHCP range:" in line:
            if self.DEBUG:
                print("new DHCP connection spotted")
            self.dnsmasq_data = ""
        self.dnsmasq_data += line + "\n"
        #print("self.dnsmasq_data is now: " + str(self.dnsmasq_data))
        if "next server:" in line:
            if self.DEBUG:
                print("end of new DHCP connection spotted")
            self.parse_dhcp()
            
        if "query[A" in line: # or "is <CNAME>" in line:
            if self.DEBUG:
                print("query[A spotted")
            
            ip = str(line.split(' ')[-1])
            if not valid_ip(ip):
                return
            
            domain = str(line.split(' ')[-3])
            if self.DEBUG:
                print("spotted DNS query by: " + ip)
                print("-it was asking for: " + domain)
            
            if ip in self.persistent_data['ip_to_mac']:
                mac = self.persistent_data['ip_to_mac'][ip]
                if self.DEBUG:
                    print("ip-to-mac gave: " + mac)
                if 'requests' not in self.persistent_data['animals'][mac]:
                    self.persistent_data['animals'][mac]['requests'] = []
                    
                # store all the details about this request, so it can be used later to asses if the behavious is malicious.
                request = {'mac':mac,'ip':ip, 'domain':domain, 'timestamp':time.time() }
                self.persistent_data['animals'][mac]['requests'].append(request)
                
                # for ease of use, also record the times that a specific domain was accessed in a list.
                if 'domains' not in self.persistent_data['animals'][mac]:
                    self.persistent_data['animals'][mac]['domains'] = {}
                    
                #if domain.startswith("www."):
                #    domain = domain.replace("www.","") # hosts file needs precise domains, so removing www might not be a great idea.
                
                if "." in domain:
                    if self.DEBUG:
                        print("a domain spotted")
                    self.last_any_domain_countdown = self.domain_countdown_time
                    self.devices['hotspot'].properties['any'].update(True)
                    
                    if domain not in self.persistent_data['animals'][mac]['domains']:
                        self.persistent_data['animals'][mac]['domains'][domain] = {}
                        self.persistent_data['animals'][mac]['domains'][domain]['timestamps'] = []
                        self.last_new_domain_countdown = self.domain_countdown_time
                        if self.DEBUG:
                            print("new domain spotted")
                        self.devices['hotspot'].properties['new'].update(True)
                        
                        if domain in self.persistent_data['master_blocklist']:
                            self.persistent_data['animals'][mac]['domains'][domain]['permission'] = 'blocked'
                            self.last_blocked_domain_countdown = self.domain_countdown_time
                            if self.DEBUG:
                                print("new domain was in blocklist")
                            self.devices['hotspot'].properties['blocked'].update(True)
                            
                        else:
                            self.persistent_data['animals'][mac]['domains'][domain]['permission'] = 'allowed'
                    else:
                        if domain in self.persistent_data['master_blocklist']:
                            self.last_blocked_domain_countdown = self.domain_countdown_time
                            self.devices['hotspot'].properties['blocked'].update(True)
                            
                    self.persistent_data['animals'][mac]['domains'][domain]['timestamps'].append( time.time() )
                    
                else:
                    if self.DEBUG:
                        print("domain didn't have a . in it. Might be chrome spamming DNS..")
                if self.DEBUG:
                    print("request added to list. It's length is now: " + str(len(self.persistent_data['animals'][mac]['domains'][domain]['timestamps'])))
            else:
                if self.DEBUG:
                    print("whoa, got a request from a mysterious ip")
                if ip.startswith('192.168.12.'):
                    arp_mac = run_command("arp -a -i uap0 | grep " + str(ip) + " | cut -f4 -' '")
                    if valid_mac(str(arp_mac)):
                        self.persistent_data['ip_to_mac'][ip] = str(arp_mac)
                        self.persistent_data['animals'][str(arp_mac)] = {}

                        self.persistent_data['animals'][str(arp_mac)]['mac'] = str(arp_mac)
                        self.persistent_data['animals'][str(arp_mac)]['nicename'] = "Unknown name"
                        self.persistent_data['animals'][str(arp_mac)]['ip'] = str(ip)
                        self.persistent_data['animals'][str(arp_mac)]['vendor'] = "Unknown vendor"
                        self.persistent_data['animals'][str(arp_mac)]['dhcp_timestamp'] = time.time()
           
            
    def parse_dhcp(self):
        if self.DEBUG:
            print("in parse_dhcp")
        dhcp_lines = self.dnsmasq_data.splitlines()
        #print("dhcp_lines = " + str(dhcp_lines))
        #print("dhcp_lines length = " + str(len(dhcp_lines)))
        new_device = {}
        for line in dhcp_lines:
            if self.DEBUG:
                print("parsing dhcp line: " + str(line))
            if 'dnsmasq-dhcp' in line:
                if "client provides name" in line:
                    print("-spotted client provides name")
                    potential_name = str(line.split(' ')[-1])
                    potential_name = potential_name.replace('-'," ")
                    potential_name = potential_name.replace('_'," ")
                    new_device['nicename'] = potential_name
					
                elif "DHCPDISCOVER(uap0)" in line:
                    if self.DEBUG:
                        print("-spotted DHCPDISCOVER")
                    potential_mac = extract_mac(line)
                    if valid_mac(potential_mac):
                        new_device['mac'] = potential_mac
						
                elif "vendor class:" in line:
                    if self.DEBUG:
                        print("-spotted vendorclass")
                    potential_vendor = str(line.split(' ')[-1])
                    potential_vendor = potential_vendor.replace('-'," ")
                    potential_vendor = potential_vendor.replace('_'," ")
                    potential_vendor = potential_vendor.replace(':'," ")
                    new_device['vendor'] = potential_vendor
					
                elif "DHCPOFFER(uap0)" in line:
                    if self.DEBUG:
                        print("-spotted DHCPOFFER")
                    potential_ip = extract_ip(line)
                    if valid_ip(potential_ip):
                        new_device['ip'] = potential_ip
						
                elif "DHCPACK(uap0)" in line or "DHCPREQUEST(uap0)" in line:
                    potential_mac = extract_mac(line)
                    if valid_mac(potential_mac):
                        new_device['mac'] = potential_mac
                    if self.DEBUG:
                        print("-should be an IP")
                    potential_ip = extract_ip(line)
                    if self.DEBUG:
                        print("potential ip = " + str(potential_ip))
                    if valid_ip(potential_ip):
                        new_device['ip'] = potential_ip
                    else:
                        if self.DEBUG:
                            print("ip was invalid?")
                        
        if self.DEBUG:
            print("new device: " + str(new_device))
        
        if 'mac' in new_device and 'ip' in new_device:
        #if hasattr(new_device, 'mac') and hasattr(new_device, 'ip'):
            if self.DEBUG:
                print("mac and IP were spotted OK")
        #if new_device['mac'] and new_device['ip']:
            if str(new_device['mac']) not in self.persistent_data['animals']:
                if self.DEBUG:
                    print("new device, has mac, so adding it.")
                self.persistent_data['animals'][str(new_device['mac'])] = {}
            else:
                if self.DEBUG:
                    print("This device was already in the persistent data. Updating the info.")
                
            if not 'vendor' in new_device:
                new_device['vendor'] = 'Unnamed'
            if not 'nicename' in new_device:
                new_device['nicename'] = 'Unnamed'
                
            if not 'animals' in self.persistent_data:
                self.persistent_data['animals'] = {}

			if not str(new_device['mac']) in self.persistent_data['animals']:
				self.persistent_data['animals'][str(new_device['mac'])] = {}
				
            self.persistent_data['animals'][str(new_device['mac'])]['mac'] = new_device['mac']
            self.persistent_data['animals'][str(new_device['mac'])]['nicename'] = new_device['nicename']
            self.persistent_data['animals'][str(new_device['mac'])]['ip'] = new_device['ip']
            self.persistent_data['animals'][str(new_device['mac'])]['vendor'] = new_device['vendor']
            self.persistent_data['animals'][str(new_device['mac'])]['dhcp_timestamp'] = time.time()
            
            if not 'ip_to_mac' in self.persistent_data:
                self.persistent_data['ip_to_mac'] = {}
                
            new_ip = new_device['ip']
            self.persistent_data['ip_to_mac'][new_ip] = new_device['mac']
        else:
            if self.DEBUG:
                print("ERROR, no valid mac and ip detected?")
                
        if self.DEBUG:
            print("")
            print("animals updated")
        #print(str(self.persistent_data['animals']))
        self.save_persistent_data()
        self.dnsmasq_data = ""
        
        
        """
        STDERR: dnsmasq-dhcp: 3805061123 available DHCP range: 192.168.12.2 -- 192.168.12.30
        STDERR: dnsmasq-dhcp: 3805061123 vendor class: android-dhcp-9
        STDERR: dnsmasq-dhcp: 3805061123 client provides name: Galaxy-Tab-A
        STDERR: dnsmasq-dhcp: 3805061123 DHCPDISCOVER(uap0) 88:29:9c:XX:XX:XX 
        STDERR: dnsmasq-dhcp: 3805061123 tags: uap0
        STDERR: dnsmasq-dhcp: 3805061123 DHCPOFFER(uap0) 192.168.12.21 88:29:XX:25:XX:XX 
        STDERR: dnsmasq-dhcp: 3805061123 requested options: 1:netmask, 3:router, 6:dns-server, 15:domain-name, 
        STDERR: dnsmasq-dhcp: 3805061123 requested options: 26:mtu, 28:broadcast, 51:lease-time, 58:T1, 
        STDERR: dnsmasq-dhcp: 3805061123 requested options: 59:T2, 43:vendor-encap
        STDERR: dnsmasq-dhcp: 3805061123 next server: 192.168.12.1
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  1 option: 53 message-type  2
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  4 option: 54 server-identifier  192.168.12.1
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  4 option: 51 lease-time  12h
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  4 option: 58 T1  6h
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  4 option: 59 T2  10h30m
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  4 option:  1 netmask  255.255.255.0
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  4 option: 28 broadcast  192.168.12.255
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  3 option: 15 domain-name  uap
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  4 option:  6 dns-server  192.168.12.1
        STDERR: dnsmasq-dhcp: 3805061123 sent size:  4 option:  3 router  192.168.12.1
        """
        
        


    def update_dnsmasq(self):
        if self.DEBUG:
            print("in update dnsmasq")
        if self.dnsmasq_pid == None:
            print("no dnsmasq PID!")
            # https://serverfault.com/questions/723292/dnsmasq-doesnt-automatically-reload-when-entry-is-added-to-etc-hosts
            return
        
        hosts_data = ""
        for domain in self.persistent_data['master_blocklist']:
            if self.DEBUG:
                print("master blocklist item: " + str(domain))
            hosts_data += "0.0.0.0 " + domain + "\n"
        
        with open(self.master_blocklist_file_path, 'w') as f:
            f.write(hosts_data)
            if self.DEBUG:
                print("saved master_blocklist hosts file : " + str(self.master_blocklist_file_path))

 
 
 
 
    def update_blocklists(self):
        if self.DEBUG:
            print("in update_blocklists")
        try:
            
            # Steve Black blocklist
            r = requests.get('https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts')
            #print(str(r.text))
            if len(r.text > 1000):
                with open(self.steven_black_blocklist_file_path, 'w') as f:
    
                    f.write(r.text)
                
                    self.persistent_data['last_trackers_update_time'] = time.time()
                    if self.DEBUG:
                        print("Succesfully downloaded latest Steven Black blocklist")        
            
            else:
                if self.DEBUG:
                    print("WARNING, Steve Black tracker list was not very long, probably an ERROR? Will try again in 10 minutes.")
                self.persistent_data['last_trackers_update_time'] = time.time() - (self.trackers_update_interval_seconds - 600) # if it failed, then try again in 10 minutes
            
            
            
            # DOWNLOAD DUCK DUCK GO BLOCKLIST
            # Only allows non-commercial use, which I cannot guarantee users will respect, so disabled for now.
            """
            r = requests.get('https://raw.githubusercontent.com/duckduckgo/tracker-blocklists/main/web/tds.json')
            #print(str(r.text))

            duck_duck_go_json = json.loads(r.text)

            if 'trackers' in duck_duck_go_json:
    
                tracking_domains = "# Blocklist curated by Duck Duck Go\n# https://github.com/duckduckgo/tracker-blocklists/\n# Licensed under the CC BY-NC-SA 4.0 license, available at https://creativecommons.org/licenses/by-nc-sa/4.0/\n"
                for key in duck_duck_go_json['trackers']:
                    tracking_domains += '0.0.0.0 ' + key + '\n'
    
                    #print(str(tracking_domains))
    
                with open(self.duck_duck_go_blocklist_file_path, 'w') as f:
    
                    if len(tracking_domains) > 100:
                        #print("that's long list, nice")
                        f.write(tracking_domains)
                    
                        self.persistent_data['last_trackers_update_time'] = time.time()
                        if self.DEBUG:
                            print("Succesfully downloaded latest Duck Duck Go blocklist")
                        
                    else:
                        if self.DEBUG:
                            print("WARNING, duck duck go tracker list was not very long, probably an ERROR? Will try again in 10 minutes.")
                        self.persistent_data['last_trackers_update_time'] = time.time() - (self.trackers_update_interval_seconds - 600) # if it failed, then try again in 10 minutes
                            
            else:
                if self.DEBUG:
                    print("ERROR, no tracker list in downloaded Duck Duck Go trackers json. Will try again in 10 minutes.")
                self.persistent_data['last_trackers_update_time'] = time.time() - (self.trackers_update_interval_seconds - 600)
                    
            """
                    
                    
            
                    
                            
        except Exception as ex:
            if self.DEBUG:
                print("Error while updating blocklists: " + str(ex))
            self.persistent_data['last_trackers_update_time'] = time.time() - (self.trackers_update_interval_seconds - 600) # if it failed, then try again in 10 minutes
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
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





#
#  UNLOAD
#

    def unload(self):
        if self.DEBUG:
            print("Shutting down Hotspot. Bye!")
        
        self.save_persistent_data()
        self.running = False
        if self.nmcli_installed == False and self.hostapd_installed == True:
            for pid in self.child_pids:
                if self.DEBUG:
                    print("- killing pid: " + str(pid))
                shell("sudo kill {}".format(pid))
                
            """
            if self.hostapd_pid != None:
                #os.kill(self.hostapd_pid, signal.SIGTERM)
                shell("sudo kill {}".format(self.hostapd_pid))
                print("hostapd process has been asked to stop")
            if self.dnsmasq_pid != None:
                #os.kill(self.dnsmasq_pid, signal.SIGTERM)
                shell("sudo kill {}".format(self.dnsmasq_pid))
                print("dnsmasq process has been asked to stop")
            
                # os.system("sudo pkill -9 -P " + str(proc.pid))
                # https://stackoverflow.com/questions/50618411/killing-sudo-started-subprocess-in-python
        
                # it IS simple to kill based on command string:
                # pkill -f "ping google.com"
            """
           
            if self.launched: 
                # remove uap0 interface
                os.system("sudo iw dev uap0 del")
                os.system("sudo ip link set dev wlan0 up")
        
                #disable transporting packets internally
                os.system("sudo sysctl -w net.ipv4.ip_forward=0")
            
                # restore services
                os.system("sudo systemctl start wpa_supplicant.service")
                os.system("sudo systemctl start dhcpcd.service")
                #os.system("sudo pkill dhcpcd")
        

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

            #with open(self.persistence_file_path) as f:
                #if self.DEBUG:
                #    print("saving persistent data: " + str(self.persistent_data))
                #pretty = json.dumps(self.persistent_data, sort_keys=True, indent=4, separators=(',', ': '))
            json.dump( self.persistent_data, open( self.persistence_file_path, 'w+' ), indent=4 )
            if self.DEBUG:
                print("Data stored")
            return True

        except Exception as ex:
            if self.DEBUG:
                print("Error: could not store data in persistent store: " + str(ex) )
                print(str(self.persistent_data))
            return False


    def update_network_info(self):
        try:
            possible_ip = get_own_ip()
            if valid_ip(possible_ip):
                self.ip_address = possible_ip
            #if self.DEBUG:
            #    print("My IP address = " + str(self.ip_address))
        except Exception as ex:
            print("Error getting own ip: " + str(ex))

        # Get hostname
        try:
            self.hostname = str(socket.gethostname())
            if self.DEBUG:
                print("fresh hostname = " + str(self.hostname))
        except Exception as ex:
            print("Error getting hostname: " + str(ex) + ", setting hostname to ip_address instead")
            self.hostname = str(self.ip_address)        
        

    def ethernet_check(self):
        check = shell('ifconfig eth0')
        if 'inet ' in check:
            return True
        else:
            return False

