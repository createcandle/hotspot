from gateway_addon import Device, Property


#
# DEVICE
#

class HotspotDevice(Device):
    """Candle device type."""

    def __init__(self, adapter):
        """
        Initialize the object.
        adapter -- the Adapter managing this device
        """

        Device.__init__(self, adapter, 'hotspot')
        
        self._id = 'hotspot'
        self.id = 'hotspot'
        self.adapter = adapter

        self.name = 'hotspot'
        self.title = 'Hotspot'
        self.description = 'Details from the Hotspot add-on'
        self._type = ['OnOffSwitch']
        self.connected = False
        
        try:
            #volume_property = HotspotProperty(self,"volume",)
            """
            self.properties["volume"] = HotspotProperty(
                            self,
                            "volume",
                            {
                                '@type': 'LevelProperty',
                                'title': "Volume",
                                'type': 'integer',
                                'minimum': 0,
                                'maximum': 100,
                                'unit':'percent'
                            },
                            0 )
            
            self.properties["status"] = HotspotProperty(
                            self,
                            "status",
                            {
                                'title': "Status",
                                'type': 'string',
                                'readOnly': True
                            },
                            "Hello")
            """
            self.properties["new"] = HotspotProperty(
                            self,
                            "new",
                            {
                                '@type':'OnOffProperty',
                                'title': 'New domain',
                                'type': 'boolean',
                                'readOnly': True
                            },
                            False )

            self.properties["any"] = HotspotProperty(
                            self,
                            "any",
                            {
                                '@type':'OnOffProperty',
                                'title': 'recent connection',
                                'type': 'boolean',
                                'readOnly': True
                            },
                            False )
                            
            self.properties["blocked"] = HotspotProperty(
                            self,
                            "blocked",
                            {
                                '@type':'OnOffProperty',
                                'title': 'blocked connection',
                                'type': 'boolean',
                                'readOnly': True
                            },
                            False )
                            
            self.properties["activity"] = HotspotProperty(
                            self,
                            "activity",
                            {
                                'title': "Activity",
                                'type': 'integer',
                                'readOnly': True
                            },
                            0)
            
            """
            self.properties["count"] = HotspotProperty(
                            self,
                            "count",
                            {
                                'title': "Count",
                                'type': 'integer',
                                'readOnly': True
                            },
                            0)
            """                 
                                
            #if self.adapter.DEBUG:
            #    print("adding audio output property to Hotspot thing with list: " + str(audio_output_list))
            """
            self.properties["audio_output"] = HotspotProperty(
                            self,
                            "audio_output",
                            {
                                'title': "Audio output",
                                'type': 'string',
                                'enum': audio_output_list
                            },
                            str(self.adapter.persistent_data['audio_output']))
                                
            if self.adapter.sound_detection:
                if self.adapter.DEBUG:
                    print("adding sound detection property")
                self.properties["sound_detected"] = HotspotProperty(
                                self,
                                "sound_detected",
                                {
                                    'title': "Sound detected",
                                    'type': 'boolean',
                                    'readOnly': True
                                },
                                False)
            """
                
                                
        except Exception as ex:
            print("error adding properties: " + str(ex))
        print("Hotspot thing has been created")
        #self.adapter.handle_device_added(self)



#
# PROPERTY
#

class HotspotProperty(Property):

    def __init__(self, device, name, description, value):
        #print("")
        #print("Init of property")
        Property.__init__(self, device, name, description)
        self.device = device
        self.name = name
        self.title = name
        self.description = description # dictionary
        self.value = value
        self.set_cached_value(value)


    def set_value(self, value):
        #print(str(value))
        try:
            if self.device.adapter.DEBUG:
                print("set_value called for: " + str(self.title))
                
            """
            if self.title == 'volume':
                self.device.adapter.set_speaker_volume(int(value))
                #self.update(value)

            if self.title == 'feedback-sounds':
                self.device.adapter.set_feedback_sounds(bool(value))
                #self.update(value)

            if self.title == 'listening':
                self.device.adapter.was_listening_when_microphone_disconnected = bool(value) # if the user consciously changes this, then override the setting.
                self.device.adapter.set_snips_state(bool(value))
                #self.update(value)
                
            if self.title == 'audio_output':
                self.device.adapter.set_audio_output(str(value))
                #self.update(value)
            """    
            
        except Exception as ex:
            print("set_value error: " + str(ex))


    def update(self, value):         
        if self.device.adapter.DEBUG:
            print("property -> update. Value = " + str(value))
        
        if value != self.value:
            
            self.value = value
            
            #set_cached_value_and_notify
            
            self.set_cached_value(value)
            self.device.notify_property_changed(self)
            if self.device.adapter.DEBUG:
                print("property updated to new value")
        #else:
        #    if self.device.adapter.DEBUG:
        #        print("property was already that value")
