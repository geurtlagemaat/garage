from bliknetlib import nodeControl

__author__ = 'geurt'

import datetime
from twisted.internet import reactor
from twisted.internet import task
from serialNodesController import SerialNodesController
import AirQuality

oNodeControl = None
airQuality = None

def eUpdateSensorData():
    airQuality.doUpdate(oNodeControl)

def onMQTTSubscribe(client, userdata, mid, granted_qos):
    oNodeControl.log.info("Subscribed: " + str(mid) + " " + str(granted_qos))

def onMQTTMessage(client, userdata, msg):
    oNodeControl.log.info("ON MESSAGE:" + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    if (msg.topic == "garage/updatecmd"):
        eUpdateSensorData()

def subscribeTopics():
    if oNodeControl.mqttClient is not None:
        oNodeControl.mqttClient.on_subscribe = onMQTTSubscribe
        oNodeControl.mqttClient.subscribe("garage/updatecmd", 0)
        oNodeControl.mqttClient.on_message = onMQTTMessage
        oNodeControl.mqttClient.loop_start()

if __name__ == '__main__':
    now = datetime.datetime.now()
    oNodeControl = nodeControl.nodeControl(r'settings/bliknetnode.conf')
    oNodeControl.log.info("BliknetNode: %s starting at: %s." % (oNodeControl.nodeID, now))

    mySerialNodesController = SerialNodesController(oNodeControl)

    # sensor upload task
    if oNodeControl.nodeProps.has_option('sensors', 'active') and \
            oNodeControl.nodeProps.getboolean('sensors', 'active'):
        airQuality = AirQuality(oNodeControl)
        if airQuality is not None:
            iUploadInt = 20
            if oNodeControl.nodeProps.has_option('sensors', 'uploadInterval'):
                iUploadInt = oNodeControl.nodeProps.getint('sensors', 'uploadInterval')
            oNodeControl.log.info("Sensor upload task active, upload interval: %s" % str(iUploadInt))
            l = task.LoopingCall(eUpdateSensorData)
            l.start(iUploadInt)
    else:
        oNodeControl.log.info("Sensor upload task not active.")

    subscribeTopics()

    if oNodeControl.nodeProps.has_option('watchdog', 'circusWatchDog'):
        if oNodeControl.nodeProps.getboolean('watchdog', 'circusWatchDog') == True:
            oNodeControl.circusNotifier.start()

    reactor.run()