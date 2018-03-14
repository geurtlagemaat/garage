# -*- coding: utf-8 -*-
import traceback
import bme680
import time

STATIONELEVATION=8.7

class AirQuality(object):

    def __init__(self, NodeControl):
        self._NodeControl = NodeControl
        self._BME680Sensor = None

        try:
            self._BME680Sensor = bme680.BME680()
            self._BME680Sensor.set_humidity_oversample(bme680.OS_2X)
            self._BME680Sensor.set_pressure_oversample(bme680.OS_4X)
            self._BME680Sensor.set_temperature_oversample(bme680.OS_8X)
            self._BME680Sensor.set_filter(bme680.FILTER_SIZE_3)
            self._BME680Sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

            self._NodeControl.log.info("Initial reading BME680:")
            for name in dir(self._BME680Sensor.data):
                value = getattr(self._BME680Sensor.data, name)

                if not name.startswith('_'):
                    self._NodeControl.log.info("{}: {}".format(name, value))

            self._BME680Sensor.set_gas_heater_temperature(320)
            self._BME680Sensor.set_gas_heater_duration(150)
            self._BME680Sensor.select_gas_heater_profile(0)

            if self._NodeControl.nodeProps.has_option('sensors','burninValue'):
                self._gas_baseline = self._NodeControl.nodeProps.get('sensors','burninValue')
            else:
                self._gas_baseline = self.doSensorBurnIn()
                NodeControl.log.info("Sensor burn in value: %s" % self._gas_baseline)
                try:
                    self._NodeControl.nodeProps.set('sensors', 'burninValue', self._gas_baseline)
                    with open(self._NodeControl.propertiesFile, 'wb') as configfile:
                        self._NodeControl.nodeProps.write(configfile)
                except Exception, exp:
                    NodeControl.log.warning("Error writing burnin value %s, error: %s." % (self._gas_baseline, traceback.format_exc()))
            # Set the humidity baseline to 40%, an optimal indoor humidity. # TODO to properties
            self._hum_baseline = 40.0
            # This sets the balance between humidity and gas reading in the
            # calculation of air_quality_score (25:75, humidity:gas) # TODO to properties
            self._hum_weighting = 0.25
        except Exception, exp:
            NodeControl.log.warning("Error BME680 init, error: %s." % (traceback.format_exc()))

    def doSensorBurnIn(self):
        """Collect gas resistance burn-in values, then use the average
                    of the last 50 values to set the upper limit for calculating
                    gas_baseline. """
        self._NodeControl.log.info("Collecting gas resistance burn-in data for 5 mins")
        start_time = time.time()
        curr_time = time.time()
        burn_in_time = 300
        burn_in_data = []
        while curr_time - start_time < burn_in_time:
            curr_time = time.time()
            if self._BME680Sensor.get_sensor_data() and self._BME680Sensor.data.heat_stable:
                gas = self._BME680Sensor.data.gas_resistance
                burn_in_data.append(gas)
                # print("Gas: {0} Ohms".format(gas))
                time.sleep(1)
        return sum(burn_in_data[-50:]) / 50.0

    def doUpdate(self, NodeControl):
        if self._BME680Sensor is not None:
            NodeControl.log.debug("Sensor Status update")
            try:
                if self._BME680Sensor.get_sensor_data():
                    Temp = '{:.1f}'.format(self._BME680Sensor.data.read_temperature)
                    Hum = '{:.1f}'.format(self._BME680Sensor.data.humidity)
                    rawPress = self._BME680Sensor.data.read_sealevel_pressure(altitude_m=STATIONELEVATION)
                    rawPresNum = int(rawPress)
                    combinedPress = "{0}.{1}".format(rawPresNum / 100, rawPresNum % 100)
                    formattedPress = '{:.1f}'.format(float(combinedPress))

                    NodeControl.MQTTPublish(sTopic="garage/temp", sValue=str(Temp), iQOS=0, bRetain=False)
                    NodeControl.MQTTPublish(sTopic="garage/luchtdruk", sValue=str(formattedPress), iQOS=0, bRetain=True)
                    NodeControl.MQTTPublish(sTopic="garage/hum", sValue=str(Hum), iQOS=0, bRetain=False)
                    if self._BME680Sensor.data.heat_stable:
                        gas = self._BME680Sensor.data.data.gas_resistance
                        gas_offset = self._gas_baseline - gas

                        hum = self._BME680Sensor.data.data.humidity
                        hum_offset = hum - self._hum_baseline

                        # Calculate hum_score as the distance from the hum_baseline.
                        if hum_offset > 0:
                            hum_score = (100 - self._hum_baseline - hum_offset) / (100 - self._hum_baseline) * (self._hum_weighting * 100)
                        else:
                            hum_score = (self._hum_baseline + hum_offset) / self._hum_baseline * (self._hum_weighting * 100)

                        # Calculate gas_score as the distance from the gas_baseline.
                        if gas_offset > 0:
                            gas_score = (gas / self._gas_baseline) * (100 - (self._hum_weighting * 100))

                        else:
                            gas_score = 100 - (self._hum_weighting * 100)

                        # Calculate air_quality_score.
                        air_quality_score = hum_score + gas_score
                        NodeControl.MQTTPublish(sTopic="garage/airquality", sValue=str(air_quality_score),iQOS=0, bRetain=False)
                    else:
                        NodeControl.log.warning("Error sensor airquality status update, sensor not ready")
                else:
                    NodeControl.log.warning("Error sensor status update, sensor not ready")
            except Exception, exp:
                NodeControl.log.warning("Error pressure status update, error: %s." % (traceback.format_exc()))

    def checkDevices(self):
        # TODO
        # checks if all devices are found (does NOT check valid readings)
        allDevicesFound = False