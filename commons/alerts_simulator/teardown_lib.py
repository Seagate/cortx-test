import logging
from libs.ras.ras_test_lib import RASTestLib
from commons.helpers.node_helper import Node
from config import CMN_CFG, RAS_VAL

LOGGER = logging.getLogger(__name__)


class AlertTearDown(RASTestLib):
    """
    Library for running teardown after alert is resolved
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
        self.nd_obj = Node(hostname=host, username=username, password=password)
        super().__init__(host, username, password)

    def enclosure_fun(self, alert_in_test: str):
        """
        Function for teardown of alerts of enclosure type
        """
        LOGGER.info("No teardown needed for %s", alert_in_test)

    def raid_fun(self, alert_in_test: str):
        """
        Function for teardown of alerts of raid type
        """
        LOGGER.info("No teardown needed for %s", alert_in_test)

    def server_fun(self, alert_in_test: str):
        """
        Function for teardown of alerts of server type
        """
        LOGGER.info("Teardown for: %s", alert_in_test)
        LOGGER.info("Retaining the original/default config")
        cm_cfg = RAS_VAL["ras_sspl_alert"]
        self.retain_config(cm_cfg["file"]["original_sspl_conf"], True)
        # TODO: Restore changed values in config files

    def server_fru_fun(self, alert_in_test: str):
        """
        Function for teardown of alerts of server_fru type
        """
        LOGGER.info("Teardown for: %s", alert_in_test)
        if alert_in_test == 'NW_PORT_FAULT':
            LOGGER.info("Check status of all network interfaces")
            status = self.health_obj.check_nw_interface_status()
            for k, v in status.items():
                if "DOWN" in v:
                    LOGGER.info("%s is down. Please check network connections and "
                                "restart tests.", k)
                    assert False, f"{k} is down. Please check network connections " \
                                  f"and restart tests."
            LOGGER.info("All network interfaces are up.")
