import traceback
from time import sleep
from bliknetlib.serialNodesProtocol import SerialNodesProtocol
from twisted.internet.serialport import SerialPort
from twisted.internet import reactor
import serial

class SerialNodesController(object):
    def __init__(self, oNodeControl):
        self._NodeControl = oNodeControl
        # TODO generic alert state dictionary
        self._PIR1Alerting = False
        self._PIR2Alerting = False
        self._ResetState = 10
        self._LDRLightStateValue = 400
        if self._NodeControl.nodeProps.has_option('ldr-reporting', 'state-value'):
            self._LDRLightStateValue = self._NodeControl.nodeProps.getint('ldr-reporting', 'state-value')

        # list all serial ports: python -m serial.tools.list_ports
        self._connectSerialPort()

    def _connectSerialPort(self):
        self.Close()
        myProtocol = SerialNodesProtocol(self._NodeControl, OnReceive=self.OnMsgReceive)
        self._serialPort = SerialPort(myProtocol, self._NodeControl.nodeProps.get('serialnodes', 'serialport'),
                                      reactor,
                                      baudrate=9600,
                                      bytesize=serial.EIGHTBITS,
                                      parity=serial.PARITY_NONE)
        sleep(1)

    def OnMsgReceive(self, RecMsg):
        myNodeID = self._NodeControl.nodeProps.get('system', 'nodeId')
        if str(RecMsg.ToAdress) == myNodeID:
            # for this node
            if int(RecMsg.Function)==1:
                # PIR alert garage
                if not self._PIR1Alerting:
                    self._PIR1Alerting = True
                    self._NodeControl.MQTTPublish(sTopic="garage/pirevent", sValue="ON",
                                                  iQOS=0,
                                                  bRetain=False)
                    reactor.callLater(self._ResetState, self.ResetPIR1State, topic="garage/pirevent")
            elif int(RecMsg.Function)==2:
                # PIR alert Werkkamer
                if not self._PIR2Alerting:
                    self._PIR2Alerting = True
                    self._NodeControl.MQTTPublish(sTopic="werkkamer/pirevent", sValue="ON",
                                                  iQOS=0,
                                                  bRetain=False)
                    reactor.callLater(self._ResetState, self.ResetState, topic="werkkamer/pirevent")
            elif int(RecMsg.Function)==3:
                # LDR garage
                if int(RecMsg.MsgValue) > self._LDRLightStateValue:
                    self._NodeControl.MQTTPublish(sTopic="garage/ldrevent", sValue="ON",
                                                  iQOS=0,
                                                  bRetain=False)
                elif int(RecMsg.MsgValue) < self._LDRLightStateValue:
                    self._NodeControl.MQTTPublish(sTopic="garage/ldrevent", sValue="OFF",
                                                  iQOS=0,
                                                  bRetain=False)
            elif int(RecMsg.Function)==4:
                # LDR Garage zolder
                if int(RecMsg.MsgValue) > self._LDRLightStateValue:
                    self._NodeControl.MQTTPublish(sTopic="garagezolder/ldrevent", sValue="ON",
                                                  iQOS=0,
                                                  bRetain=False)
                elif int(RecMsg.MsgValue) < self._LDRLightStateValue:
                    self._NodeControl.MQTTPublish(sTopic="garagezolder/ldrevent", sValue="OFF",
                                                  iQOS=0,
                                                  bRetain=False)

    def ResetPIR1State(self, topic):
        self._PIR1Alerting = False
        self._NodeControl.MQTTPublish(sTopic="garage/pirevent", sValue="OFF", iQOS=0, bRetain=False)

    def ResetPIR2State(self, topic):
        self._PIR2Alerting = False
        self._NodeControl.MQTTPublish(sTopic="werkkamer/pirevent", sValue="OFF", iQOS=0, bRetain=False)

    def SendMessage(self, sSerialMessage):
        try:
            self._serialPort.write(sSerialMessage)
            sleep(0.1)
            return True
        except Exception, exp:
            print traceback.format_exc()
            self._NodeControl.log.error("SendMessage error: %s." % traceback.format_exc())
            return False

    def Close(self):
        try:
            self._serialPort.loseConnection()
            self._serialPort = None
        except:
            pass