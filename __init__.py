'''
Created on Aug 31, 2017

@author: deevrek
'''
import sys
from os.path import dirname, abspath, basename
import time
sys.path.append(abspath(dirname(__file__)))
HAssistantSkill = __import__('HAssistant').HAssistantSkill


from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

logger = getLogger(__name__)

class HAChatbotSkill(HAssistantSkill):
    def __init__(self):
        super(HAChatbotSkill, self).__init__('HAChatbotSkill')

    def initialize(self):
        logger.info('Initializing HAChatbotSkill')
        super(HAChatbotSkill, self).initialize()
        self.run()
        
    def ha_connected(self):
        self.register_event('MycroftTell',handler=self.tell)
        self.register_event('telegram_text',handler=self.telegram)
        
    def send_utterance(self,utterance):
        if not utterance==None:
            ##TODO Language!!
            mycroft_message={"lang": "en-us", "utterances": [utterance]}
            self.emitter.emit(
                Message('recognizer_loop:utterance',mycroft_message))
    
    def tell(self,event_message):
        ha_utterance=event_message.get("utterance")
        self.send_utterance(ha_utterance)
        
    def _handle_speak(self,message):
        self.telegram_reply(message.data.get('utterance'))
        
    def telegram(self,event_message):
        ha_utterance=event_message.get("text")
        self.send_utterance(ha_utterance)
        self.emitter.on('speak',self._handle_speak)
        time.sleep(5)
        self.emitter.remove_all_listeners('speak')
                
    def telegram_reply(self,text):
        self.call_service('notify','telegram_send',{"message" : text})
            
def create_skill():
    return HAChatbotSkill()