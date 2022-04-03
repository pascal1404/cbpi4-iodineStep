import os
from aiohttp import web
import logging
import asyncio
import random
from cbpi.api import *
from cbpi.api.step import StepResult, CBPiStep
from cbpi.api.timer import Timer
from datetime import datetime
import time
from voluptuous.schema_builder import message
from cbpi.api.dataclasses import NotificationAction, NotificationType
from cbpi.api.dataclasses import Kettle, Props
from socket import timeout
from cbpi.api.config import ConfigType
from cbpi.api.base import CBPiBase
from cbpi.api import parameters, Property, action
from typing import KeysView
import numpy as np
import warnings

logger = logging.getLogger(__name__)

@parameters([Property.Number(label="Timer", description="Time in Minutes", configurable=True), 
             Property.Number(label="Temp", configurable=True),
             Property.Sensor(label="Sensor"),
             Property.Kettle(label="Kettle"),])
class IodineStep(CBPiStep):

    async def NextStep(self, **kwargs):
        self.init = True
        self.cbpi.notify('Yes', 'Iodine check successfull', NotificationType.INFO)
        await self.next()

    @action("Add 5 Minutes to Timer", [])
    async def add_timer(self):
        if self.timer.is_running == True:
            self.cbpi.notify(self.name, '5 Minutes added', NotificationType.INFO)
            await self.timer.add(300)       
        else:
            self.cbpi.notify(self.name, 'Timer must be running to add time', NotificationType.WARNING)

    async def start_timer(self):
        self.cbpi.notify('No', "Iodine check not successfull! Starting additional {} minutes at {}°{}".format(self.props.get("Timer",0),self.props.get("Temp",0),self.cbpi.config.get("TEMP_UNIT", "C")), NotificationType.INFO)

        if self.cbpi.kettle is not None:
            self.kettle.target_temp = int(self.props.get("Temp", 0))
            await self.setAutoMode(True)
            await self.push_update()
            self.timer = Timer(int(self.props.get("Timer",0)) *60 ,on_update=self.on_timer_update, on_done=self.on_timer_done)

        if self.timer.is_running is not True:
            self.timer.start()
            self.timer.is_running = True
        else:
            await self.timer.add(int(self.props.get("Timer",0)) *60)

        await self.push_update()

    async def on_timer_done(self,timer):
        self.summary = "Iodine check successfull?"
        if self.kettle is not None:
            await self.setAutoMode(False)
            self.kettle.target_temp = 0
        if self.remaining_seconds < 2:
            self.cbpi.notify(self.name, "Iodine check successfull?", NotificationType.INFO, action=[NotificationAction("Yes", self.NextStep), NotificationAction("No", self.start_timer)])
        await self.push_update()

    async def on_timer_update(self,timer, seconds):
        self.summary = Timer.format_time(seconds)
        self.remaining_seconds = seconds
        await self.push_update()

    async def on_start(self):
        self.summary=""
        self.kettle=self.get_kettle(self.props.Kettle)
        if self.kettle is not None:
            self.kettle.target_temp = int(self.props.get("Temp", 0))
            await self.setAutoMode(True)
        self.init = True
        if self.timer is None:
            self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        else:
            self.timer.start()
            self.timer.is_running = True
        await self.push_update()

    async def on_stop(self):
        await self.timer.stop()
        self.summary = ""
        if self.kettle is not None:
            await self.setAutoMode(False)
        self.init = True
        await self.push_update()
        
    async def reset(self):
        await self.timer.stop()
        self.summary = ""
        self.init = True
        self.timer = Timer(1 ,on_update=self.on_timer_update, on_done=self.on_timer_done)
        await self.push_update()

    async def run(self):
        while self.running == True:
            await asyncio.sleep(1)
            if self.init == True:
                self.init = False
                if self.timer.is_running is not True:
                    self.timer.start()
                    self.timer.is_running = True
            else:
                sensor_value = self.get_sensor_value(self.props.get("Sensor", None)).get("value")
                if sensor_value >= int(self.props.get("Temp",0)) and self.timer.is_running is not True:
                    self.timer.start()
                    self.timer.is_running = True
        return StepResult.DONE

    async def setAutoMode(self, auto_state):
        try:
            if (self.kettle.instance is None or self.kettle.instance.state == False) and (auto_state is True):
                await self.cbpi.kettle.toggle(self.kettle.id)
            elif (self.kettle.instance.state == True) and (auto_state is False):
                await self.cbpi.kettle.stop(self.kettle.id)
            await self.push_update()

        except Exception as e:
            logging.error("Failed to switch on KettleLogic {} {}".format(self.kettle.id, e))


def setup(cbpi):
    cbpi.plugin.register("IodineStep", IodineStep)
