'''
Created on Aug 30, 2017

@author: deevrek
'''
from websocket import WebSocketApp
import thread
import time
import json

from mycroft.configuration import ConfigurationManager
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

logger = getLogger(__name__)

class HAssistantSkill(MycroftSkill):
    def __init__(self, name):
        super(HAssistantSkill, self).__init__(name)
        config = ConfigurationManager.get()
        self.base_conf = config.get('HomeAssistantSkill')
        self.password=self.base_conf.get('password')
        self.timeout=self.base_conf.get('timeout',30)
        url=self.build_url(self.base_conf.get('host'), self.base_conf.get('port'),
                                    '/api/websocket',self.base_conf.get('ssl'))
        self.ha_ws = WebSocketApp(url,
                                on_error = self.on_error,
                                on_close = self.on_close)
        self.ha_events={}
        self.ha_handlers={}
        self.event_index=1
        self.waiting=0
        self.response=None
        
    def build_url(self, host, port, route, ssl):
        scheme = "wss" if ssl else "ws"
        url = scheme + "://" + host + ":" + str(port) + route
        return url              

    def initialize(self):
        logger.info('Initializing HomeAssistantSkill commons')
        self.ha_ws.on_open = self.on_open
                
        
    def register_event(self,event_type,handler):
        logger.info("listener %s active" % event_type)
        self.event_index+=1
        event={event_type:self.event_index}
        handler={event_type:handler}
        self.ha_events.update(event)
        self.ha_handlers.update(handler)
        self.ha_ws.send(json.dumps({
            'id': self.event_index,
            'type': 'subscribe_events',
            'event_type': event_type                                     
            }))
        
    def unregister_event(self,event_type):
        logger.info("Removing listener %s" % event_type)
        self.ha_events.pop(event_type)
        self.ha_handlers.pop(event_type)
        self.event_index+=1
        self.ha_ws.send(json.dumps({
              "id": self.event_index,
              "type": "unsubscribe_events",
              "subscription": self.ha_events.get(event_type)
            }))
        
    def shutdown(self):
        super(MycroftSkill,self).shutdown()
        for k,v in self.ha_events:
            self.unregister_event(k)
                        
    def on_message(self,ws, message):
        logger.debug("ha event:%s" % message)
        message_data=json.loads(message)
        message_type=message_data.get('type')
        if  message_type == 'event':
            event_type=message_data.get('event').get('event_type') 
            if event_type in self.ha_events:            
                event_data=message_data.get('event').get('data')   
                try:
                    self.ha_handlers[event_type](event_data)
                except:
                    logger.error("handlerfailed for event %s" % event_type)
        elif message_type=='auth_ok':
            logger.info("Connected to Home Assistant")
            self.ha_connected()
        elif message_type == 'result':
            self.on_result(message_data)
                
    def _wait_response(self,timeout):
        start = time.time()
        elapsed = 0
        while self.waiting > 0 and elapsed < timeout:
            elapsed = time.time() - start
            time.sleep(0.1)
        self.waiting = 0        
            
    def call_service(self,domain,service,attributes=None):
        self.event_index+=1
        payload={
              "id": self.event_index,
              "type": "call_service",
              "domain": domain,
              "service": service
        }
        if isinstance(attributes, dict):
            payload['service_data']=attributes
        self.waiting=self.event_index
        self.response=None
        self.ha_ws.send(json.dumps(payload))
        self._wait_response(self.timeout)
        return self.response
        
    def ha_connected(self):
        pass
    
    def on_result(self,message):
        if message.get('id')==self.waiting:
            self.waiting=0
            self.response=message.get('result')
    
    def on_error(self,ws, error):
        logger.error(error)
    
    def on_close(self,ws):
        logger.info("Websocket to homeassistant closed")
    
    def on_open(self,ws):
        if self.password:
            ws.send(json.dumps({"type": "auth", "api_password": self.password}))
        else:
            self.ha_connected()
        ws.on_message = self.on_message

    def run(self):
        self.ha_ws.run_forever()
