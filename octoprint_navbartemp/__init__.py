# coding=utf-8
from __future__ import absolute_import

__author__ = "Jarek Szczepanski <imrahil@imrahil.com>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 Jarek Szczepanski - Released under terms of the AGPLv3 License"

import octoprint.plugin
from octoprint.util import RepeatedTimer
import sys, getopt
import re
import os                                                  # import os module
import glob                                                # import glob module
import time                                                # import time module



class NavBarPlugin(octoprint.plugin.StartupPlugin,
                   octoprint.plugin.TemplatePlugin,
                   octoprint.plugin.AssetPlugin,
                   octoprint.plugin.SettingsPlugin):

    def __init__(self):
        self.isRaspi = False
        self.debugMode = True      # to simulate temp on Win/Mac
        self.displayRaspiTemp = True
        self.displayAirTemp = True
        #self.maxAirTemp = True
        #self.relayPinForAirTemp = True
        self._checkTempTimer = None

    def on_after_startup(self):
        self.displayRaspiTemp = self._settings.get(["displayRaspiTemp"])
        self._logger.debug("displayRaspiTemp: %s" % self.displayRaspiTemp)
        
        self.displayAirTemp = self._settings.get(["displayAirTemp"])
        self._logger.debug("displayAirTemp: %s" % self.displayAirTemp)
        
        #self.maxAirTemp = self._settings.get(["maxAirTemp"])
        #self.relayPinForAirTemp = self._settings.get(["relayPinForAirTemp"])

        if sys.platform == "linux2":
            with open('/proc/cpuinfo', 'r') as infile:
                    cpuinfo = infile.read()
            # Match a line like 'Hardware   : BCM2709'
            match = re.search('^Hardware\s+:\s+(\w+)$', cpuinfo, flags=re.MULTILINE | re.IGNORECASE)

            if match is None:
                # Couldn't find the hardware, assume it isn't a pi.
                self.isRaspi = False
            elif match.group(1) == 'BCM2708':
                self._logger.debug("Pi 1")
                self.isRaspi = True
            elif match.group(1) == 'BCM2709':
                self._logger.debug("Pi 2")
                self.isRaspi = True
            elif match.group(1) == 'BCM2835':
                self._logger.debug("Pi 3")
                self.isRaspi = True

            if self.isRaspi and self.displayRaspiTemp:
                self._logger.debug("Let's start RepeatedTimer!")
                self.startTimer(30.0)
        elif self.debugMode:
            self.isRaspi = True
            if self.displayRaspiTemp or self.displayAirTemp:
                self.startTimer(5.0)

        self._logger.debug("is Raspberry Pi? - %s" % self.isRaspi)

    def startTimer(self, interval):
        self._checkTempTimer = RepeatedTimer(interval, self.checkAllTemperatures, None, None, True)
        self._checkTempTimer.start()
    
    def checkAllTemperatures(self):
        from sarge import run, Capture

        self._logger.debug("Checking Raspberry Pi internal temperature")

        if sys.platform == "linux2":
            p = run("/opt/vc/bin/vcgencmd measure_temp", stdout=Capture())
            p = p.stdout.text
            ap = run("/home/pi/scripts/prntScritps/scripts/airtemp.sh", stdout=Capture())
            atemp = ap.stdout.text

        elif self.debugMode:
            import random
            def randrange_float(start, stop, step):
                return random.randint(0, int((stop - start) / step)) * step + start
            p = "temp=%s'C" % randrange_float(5, 60, 0.1)
            atemp = randrange_float(-10, 40, 0.1)

        self._logger.debug("response from sarge: %s" % p)
        self._logger.debug("response from airtemp: %s" % atemp)

        match = re.search('=(.*)\'', p)
        if not match:
            self.isRaspi = False
        else:
            temp = match.group(1)
            self._logger.debug("match: %s" % temp)
            if self.displayAirTemp and self.displayRaspiTemp:
                self._plugin_manager.send_plugin_message(self._identifier, dict(israspi=self.isRaspi, raspitemp=temp, airtemp=atemp))
            elif self.displayAirTemp:
                self._plugin_manager.send_plugin_message(self._identifier, dict(israspi=self.isRaspi, airtemp=atemp))
            elif self.displayRaspiTemp:
                self._plugin_manager.send_plugin_message(self._identifier, dict(israspi=self.isRaspi, raspitemp=temp))
    
    def checkAirTemp(self):
        
        self._logger.debug("Checking air temperature of box")
        
        if sys.platform == "linux2":
            p = run("/home/pi/scripts/prntScritps/scripts/airtemp.sh", stdout=Capture())
            p = "temp=%s'C" % p.stdout.text

        elif self.debugMode:
            import random
            def randrange_float(start, stop, step):
                return random.randint(0, int((stop - start) / step)) * step + start
            p = "temp=%s'C" % randrange_float(5, 60, 0.1)

        self._logger.debug("response from TempSensor: %s" % p)
        
        match = re.search('=(.*)\'', p)
        if match:
            temp = match.group(1)
            self._logger.debug("match: %s" % temp)
            self._plugin_manager.send_plugin_message(self._identifier, dict(airtemp=temp))
        
    
    def checkRaspiTemp(self):
        from sarge import run, Capture

        self._logger.debug("Checking Raspberry Pi internal temperature")

        if sys.platform == "linux2":
            p = run("/opt/vc/bin/vcgencmd measure_temp", stdout=Capture())
            p = p.stdout.text

        elif self.debugMode:
            import random
            def randrange_float(start, stop, step):
                return random.randint(0, int((stop - start) / step)) * step + start
            p = "temp=%s'C" % randrange_float(5, 60, 0.1)

        self._logger.debug("response from sarge: %s" % p)

        match = re.search('=(.*)\'', p)
        if not match:
            self.isRaspi = False
        else:
            temp = match.group(1)
            self._logger.debug("match: %s" % temp)
            self._plugin_manager.send_plugin_message(self._identifier, dict(israspi=self.isRaspi, raspitemp=temp))


	##~~ SettingsPlugin
    def get_settings_defaults(self):
        return dict(displayRaspiTemp = self.displayRaspiTemp, displayAirTemp = self.displayAirTemp )#, maxAirTemp = self.maxAirTemp, relayPinForAirTemp = self.relayPinForAirTemp)

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        self.displayRaspiTemp = self._settings.get(["displayRaspiTemp"])
        self.displayAirTemp = self._settings.get(["displayAirTemp"])
        #self.maxAirTemp = self._settings.get(["maxAirTemp"])
        #self.relayPinForAirTemp = self._settings.get(["relayPinForAirTemp"])

        if self.displayRaspiTemp or self.displayAirTemp:
            interval = 5.0 if self.debugMode else 30.0
            self.startTimer(interval)
        else:
            if self._checkTempTimer is not None:
                try:
                    self._checkTempTimer.cancel()
                except:
                    pass
            self._plugin_manager.send_plugin_message(self._identifier, dict())

	##~~ TemplatePlugin API
    def get_template_configs(self):
        if self.isRaspi:
            return [
                dict(type="settings", template="navbartemp_settings_raspi.jinja2")
            ]
        else:
            return []

    ##~~ AssetPlugin API
    def get_assets(self):
        return {
            "js": ["js/navbartemp.js"],
            "css": ["css/navbartemp.css"],
            "less": ["less/navbartemp.less"]
        } 

    ##~~ Softwareupdate hook
    def get_update_information(self):
        return dict(
            navbartemp=dict(
                displayName="Navbar Temperature Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="imrahil",
                repo="OctoPrint-NavbarTemp",
                current=self._plugin_version,

                # update method: pip w/ dependency links
                pip="https://github.com/imrahil/OctoPrint-NavbarTemp/archive/{target_version}.zip"
            )
        )

__plugin_name__ = "Navbar Temperature Plugin"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = NavBarPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
