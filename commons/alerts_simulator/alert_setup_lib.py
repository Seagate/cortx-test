import os
import time
import random
import logging
import pytest
import pandas as pd
from libs.ras.ras_test_lib import RASTestLib
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from commons.helpers.controller_helper import ControllerLib
from libs.s3 import S3H_OBJ
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons import constants as cons
from commons import commands as common_cmd
from commons.utils.assert_utils import *
from libs.csm.rest.csm_rest_alert import SystemAlerts
from commons.alerts_simulator.generate_alert_lib import \
     GenerateAlertLib, AlertType
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG

LOGGER = logging.getLogger(__name__)


class AlertSetup(RASTestLib):
    """

    """
    def __init__(
            self,
            host: str = CMN_CFG["nodes"][0]["host"],
            username: str = CMN_CFG["nodes"][0]["username"],
            password: str = CMN_CFG["nodes"][0]["password"]) -> None:
        """
        Method initializes members of AlertSetupLib and its parent class

        :param str host: host
        :param str username: username
        :param str password: password
        """
        self.host = host
        self.username = username
        self.pwd = password
        super().__init__(host, username, password)

    def enclosure_setup
    def raid_setup
    def server_setup
    def server_fru_setup