import os
import time
import random
import logging
import pytest
import pandas as pd
import threading
from commons.alerts_simulator.generate_alert_lib import \
     GenerateAlertLib, AlertType
from commons.alerts_simulator.constants_random_alert_generation import FaultAlerts
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG

LOGGER = logging.getLogger(__name__)


class RandomAlerts:
    """
    Generate random alerts in background
    """
    def __init__(self, host=CMN_CFG["nodes"][0]["host"],
                 h_user=CMN_CFG["nodes"][0]["username"],
                 h_pwd=CMN_CFG["nodes"][0]["password"],
                 enclosure_ip=CMN_CFG["enclosure"]["primary_enclosure_ip"],
                 enclosure_user=CMN_CFG["enclosure"]["enclosure_user"],
                 enclosure_pwd=CMN_CFG["enclosure"]["enclosure_pwd"]):
        self.host_details = {"host": host, "host_user": h_user,
                             "host_password": h_pwd}
        self.enclosure_details = {"enclosure_ip": enclosure_ip,
                                  "enclosure_user": enclosure_user,
                                  "enclosure_pwd": enclosure_pwd}
        self.setup_type = CMN_CFG['setup_type']

    def generate_random_alerts(self, alert_in_test: str = None):
        """
        API to generate random alerts in background
        """
        LOGGER.info("Starting Random Alert Generation")
        import pdb
        pdb.set_trace()
        while True:
            alert = random.choice(list(FaultAlerts))
            alert_dict = alert.value
            print(alert)
            if self.setup_type == "VM" and alert_dict.get('support') != 'VM':
                continue

            # if alert.name.find("RESOLVED") == -1 and \
            #     alert.name.find("ENABLE") == -1 and \
            #         alert.name.find("RAID_ASSEMBLE") == -1 and \
            #         alert.name.find("RAID_ADD") == -1:
            #     break

            if alert_in_test != alert_dict["alert_type"]:
                LOGGER.info("Running setup for %s alert type",
                            alert_dict["alert_type"])













