"""Hotspot API handler."""

import os
import re
import json
import copy
import time
from time import sleep
#import socket
from signal import SIGHUP
import requests
import subprocess
#import threading

#from .util import valid_ip, arpa_detect_gateways

#from datetime import datetime,timedelta
#from dateutil import tz
#from dateutil.parser import *

try:
    from gateway_addon import APIHandler, APIResponse
    #print("succesfully loaded APIHandler and APIResponse from gateway_addon")
except:
    print("Import APIHandler and APIResponse from gateway_addon failed. Use at least WebThings Gateway version 0.10")
    sys.exit(1)



class HotspotAPIHandler(APIHandler):
    """Hotspot API handler."""

    def __init__(self, adapter, verbose=False):
        """Initialize the object."""
        #print("INSIDE API HANDLER INIT")
        
        self.adapter = adapter
        #self.addon_name = 'hootspot-handler'
        self.DEBUG = self.adapter.DEBUG

            
        # Intiate extension addon API handler
        try:
            manifest_fname = os.path.join(
                os.path.dirname(__file__),
                '..',
                'manifest.json'
            )

            with open(manifest_fname, 'rt') as f:
                manifest = json.load(f)

            #print("manifest id in hotspot handler: " + str(manifest['id']))
            APIHandler.__init__(self, manifest['id'])
            self.manager_proxy.add_api_handler(self)
            

            if self.DEBUG:
                print("self.manager_proxy = " + str(self.manager_proxy))
                print("Created new API HANDLER: " + str(manifest['id']))
        
        except Exception as e:
            print("Failed to init UX extension API handler: " + str(e))

        
        

#
#  HANDLE REQUEST
#

    def handle_request(self, request):
        """
        Handle a new API request for this handler.

        request -- APIRequest object
        """
        if self.DEBUG:
            print("> > >  REQUEST < < <")
        try:
        
            if request.method != 'POST':
                print("- was bot a POST request, ignoring")
                return APIResponse(status=404)
            
            if request.path == '/ajax':
                
                action = str(request.body['action'])    
                print("ajax action = " + str(action))
                
                if action == 'init':
                    print('ajax handling init')
                    print("self.adapter.persistent_data = " + str(self.adapter.persistent_data))
                    return APIResponse(
                      status=200,
                      content_type='application/json',
                      content=json.dumps({'state' : True, 'message' : 'initialization complete', 'ssid':self.adapter.ssid, 'password':self.adapter.hotspot_password , 'cable_needed':self.adapter.cable_needed, 'debug': self.DEBUG}),
                    )
                    
                elif action == 'latest':
                    print('ajax handling latest')
                    #print("self.persistent_data = " + str(self.persistent_data))
                    filtered_animals = {}
                    try:
                        filtered_animals = self.filter_animals()
                    except:
                        print("Error while filtering animals")
                    
                    print("self.adapter.seconds = " + str(self.adapter.seconds))
                    
                    return APIResponse(
                      status=200,
                      content_type='application/json',
                      content=json.dumps({'state' : True, 'message' : 'updated data received', 'animals': filtered_animals, 'master_blocklist': self.adapter.persistent_data['master_blocklist'], 'seconds':self.adapter.seconds }),
                    )
                    
                elif action == 'abort':
                    print('ajax handling abort')
                    #print("self.persistent_data = " + str(self.persistent_data))
                    self.adapter.allow_launch = False
                    return APIResponse(
                      status=200,
                      content_type='application/json',
                      content=json.dumps({'state' : True, 'message' : 'launch has been aborted' }),
                    )
                    
                elif action == 'launch':
                    print('ajax handling abort')
                    #print("self.persistent_data = " + str(self.persistent_data))
                    self.adapter.allow_launch = True
                    self.adapter.seconds == 89
                    
                    return APIResponse(
                      status=200,
                      content_type='application/json',
                      content=json.dumps({'state' : True, 'message' : 'launch has been aborted' }),
                    )
                    
                elif action == 'delete' or action == 'clear':
                    print('ajax handling delete')
                    #print("self.persistent_data = " + str(self.persistent_data))
                    mac = str(request.body['mac'])
                    state = False
                    try:
                        #self.adapter.persistent_data['animals'].pop(mac);
                        self.adapter.persistent_data['animals'][mac]['requests'] = []
                        self.adapter.persistent_data['animals'][mac]['domains'] = {}
                        self.adapter.persistent_data['animals'][mac]['delete_timestamp'] = time.time()
                        state = True
                        self.adapter.save_persistent_data()
                    except Exception as ex:
                        print("failed to delete item from dictionary")
                    
                    return APIResponse(
                      status=200,
                      content_type='application/json',
                      content=json.dumps({'state' : state, 'message' : 'Connections record was reset' }),
                    )
                    
                elif action == 'set_permission':
                    mac = str(request.body['mac'])
                    domain = str(request.body['domain'])
                    permission = str(request.body['permission'])
                    print("permission = " + permission)
                    print("permission domain = " + domain)
                    print("permission mac = " + mac)
                    self.adapter.persistent_data['animals'][mac]['domains'][domain]['permission'] = permission
                    
                    if permission == 'allowed' and domain in self.adapter.persistent_data['master_blocklist']:
                        print("- should remove domain from blocklist")
                        self.adapter.persistent_data['master_blocklist'].remove(domain)
                        self.adapter.update_dnsmasq()
                        
                        if self.adapter.dnsmasq_pid != None:
                            print("sending sighup to " + str(self.adapter.dnsmasq_pid))
                            #os.kill(self.adapter.dnsmasq_pid, SIGHUP)
                            #os.system("sudo kill -SIGHUP " + str(self.adapter.dnsmasq_pid))
                            os.system("sudo kill -s HUP " + str(self.adapter.dnsmasq_pid))
                            # sudo kill -s HUP $pid
                        
                    if permission == 'blocked' and domain not in self.adapter.persistent_data['master_blocklist']:
                        print("- should add domain to blocklist")
                        self.adapter.persistent_data['master_blocklist'].append(domain)
                        self.adapter.update_dnsmasq()
                        
                    
                    self.adapter.save_persistent_data()
                    

                        
                    
                    return APIResponse(
                      status=200,
                      content_type='application/json',
                      content=json.dumps({'state' : True, 'message': 'permission was changed', 'animals':self.adapter.persistent_data['animals'] }),
                    )
                    
                elif action == 'remove_from_master_blocklist':
                    self.adapter.persistent_data['master_blocklist'].remove(request.body['domain'])
                    #print("self.persistent_data['thing_settings'] = " + str(self.persistent_data['thing_settings'])) 
                    self.adapter.save_persistent_data()
                     
                    return APIResponse(
                      status=200,
                      content_type='application/json',
                      content=json.dumps({'state' : True, 'message': 'domain removed succesfully'}),
                    )
                    
                elif action == 'add_to_master_blocklist':
                    self.adapter.persistent_data['master_blocklist'].append(request.body['domain'])
                    #print("self.persistent_data['thing_settings'] = " + str(self.persistent_data['thing_settings'])) 
                    self.adapter.save_persistent_data()
                     
                    return APIResponse(
                      status=200,
                      content_type='application/json',
                      content=json.dumps({'state' : True, 'message': 'settings saved succesfully'}),
                    )
                else:
                    return APIResponse(status=404)
                    
            else:
                return APIResponse(status=404)
                
        except Exception as e:
            print("Failed to handle UX extension API request: " + str(e))
            return APIResponse(
              status=500,
              content_type='application/json',
              content=json.dumps("API Error"),
            )


    #
    #  This removes privacy sensitive data before it's sent over the network. 
    #              E.g. detect any normal computers and filter those out.
    #
    def filter_animals(self):
        

        
        #print("in filtering animals")
        #raw_animals = {}
        #animals_to_remove = []
        #old_animals = dict(self.adapter.persistent_data['animals'])
        new_animals = copy.deepcopy(self.adapter.persistent_data['animals'])
        #print("old animals:")
        #print(str(old_animals))
        
        try:
            #raw_animals = self.adapter.persistent_data['animals']
            #print("raw animals = " + str(raw_animals))
            #print("will loop over animals:")
            for animal in new_animals.copy():
                #print("animal: " + str(animal))
                if 'domains' in new_animals[animal]:
                    animal_count = len(new_animals[animal]['domains'].keys())
                    #print("animal count = " + str(animal_count))
                    if animal_count > 30:
                        print("removing device with a lot of domains for privacy reasons: " + str(animal))
                        #del new_animals[animal]['domains']
                        #del new_animals[animal]['requests']
                        new_animals[animal]['domains'] = {}
                        new_animals[animal]['requests'] = []
                        new_animals[animal]['protected'] = True
                    
        
        except Exception as ex:
            print("Error while filtering out privacy sensitive data: " + str(ex))
            return {"error":"Error while doing privacy filtering: "  + str(ex) }
        


        # TODO DEBUG TEMPORARY
        #return self.adapter.persistent_data['animals']
        return new_animals
        
        
        

        
        