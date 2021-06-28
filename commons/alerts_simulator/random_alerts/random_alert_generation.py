import time
import random
import logging
from commons.alerts_simulator.generate_alert_lib import \
     GenerateAlertLib, AlertType
from commons.alerts_simulator.random_alerts.constants_random_alert_generation import FaultAlerts
from commons.alerts_simulator.random_alerts.alert_setup_lib import AlertSetup
from commons.alerts_simulator.random_alerts.teardown_lib import AlertTearDown
from config import CMN_CFG

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
        self.alert_setup = AlertSetup(host=host, username=h_user,
                                      password=h_pwd)
        self.alert_teardown = AlertTearDown(host=host, username=h_user,
                                            password=h_pwd)
        self.alert_api_obj = GenerateAlertLib()

    def generate_random_alerts(self, event, ignore_alert: list = None,
                               monitor: bool = True):
        """
        API to generate random alerts in background
        :param event: Event to indicate if main thread is about to exit
        :param ignore_alert: List if alerts to be ignored during random alert
        generation
        :param monitor: Flag to indicate if monitor tests are running in main
        thread
        """
        LOGGER.info("Starting Random Alert Generation")
        ignore_alert_type = []       # collect type of alerts to be ignored
        if ignore_alert is not None:
            for a in ignore_alert:
                t = eval('FaultAlerts.{}'.format(a)).value["alert_type"]
                ignore_alert_type.append(t)

        while not event.is_set():
            alert = random.choice(list(FaultAlerts))
            alert_dict = alert.value
            LOGGER.info("Selected alert: %s", alert)
            # If selected alert is not supported on VM and if selected alert
            # is in ignore_alert list, it will continue
            if (self.setup_type == 'VM' and alert_dict.get('support') !=
                    'VM') or (ignore_alert and alert.name in ignore_alert):
                continue

            # Each alert requires different kind of setup depending on alert
            # type.
            if not monitor or alert_dict["alert_type"] not in ignore_alert_type:
                LOGGER.info("Running setup for %s alert type",
                            alert_dict["alert_type"])
                command = f"self.alert_setup.{alert_dict['function']}(alert_in_test='{alert.name}')"
                LOGGER.info("Running command %s", command)
                resp = eval(command)
                if not resp[0]:
                    continue

            # Not adding PUBLIC_DATA_FAULT in the list as to create
            # PUBLIC_DATA_FAULT we have to use management credentials for
            # running main thread
            alert_name = random.choice(['MGMT_FAULT']) \
                if alert.name == 'NW_PORT_FAULT' else alert.name
            h_details, ip_params = self.alert_setup.get_runtime_input_params(alert_name=alert_name)
            host_details = h_details if h_details is not None else self.host_details
            if alert_dict["alert_type"] == 'raid' and \
                    alert_dict["alert_type"] not in ignore_alert_type:
                ip_params["md_device"] = resp[1]
                ip_params["disk"] = resp[3]

            LOGGER.info("Generating alert %s", alert.name)
            a_t = eval(f"AlertType.{alert.name}")
            resp = self.alert_api_obj.generate_alert(alert_type=a_t,
                                                     host_details=host_details,
                                                     enclosure_details=self.enclosure_details,
                                                     input_parameters=ip_params)

            if not resp[0]:
                LOGGER.error("Failed to generate alert %s", alert.name)
                continue
            else:
                LOGGER.info("Successfully generated alert %s", alert.name)

            time.sleep(30)

            # Get enum name of the alert to be resolved
            if alert_dict.get('resolve') is not None:
                LOGGER.info("Resolving alert %s", alert.name)
                alert_name = alert_name if alert.name == 'NW_PORT_FAULT' else alert_dict.get('resolve')
                h_details, ip_params = self.alert_setup.get_runtime_input_params(
                    alert_name=alert_name)

                host_details = h_details if h_details is not None else self.host_details

                if alert_dict.get('resolve') == 'DG_FAULT_RESOLVED':
                    ip_params['phy_num'] = resp[1]
                elif alert_dict["alert_type"] == 'raid' and \
                        alert_dict["alert_type"] not in ignore_alert_type:
                    ip_params["md_device"] = resp[1]
                    ip_params["disk"] = resp[3]

                r_t = eval(f"AlertType.{alert_dict['resolve']}")
                resp = self.alert_api_obj.generate_alert(alert_type=r_t,
                                                         host_details=host_details,
                                                         enclosure_details=self.enclosure_details,
                                                         input_parameters=ip_params)

                if not resp[0]:
                    LOGGER.error("Failed to resolve alert %s", alert.name)
                else:
                    LOGGER.info("Successfully resolved alert %s", alert.name)

            # Each alert type has different teardown sequence
            if not monitor or alert_dict["alert_type"] not in ignore_alert_type:
                LOGGER.info("Running teardown for %s alert type",
                            alert_dict["alert_type"])
                command = f"self.alert_teardown.{alert_dict['function']}(alert_in_test='{alert.name}')"
                LOGGER.info("Running command %s", command)
                resp = eval(command)
                if not resp[0]:
                    continue
            else:
                LOGGER.info("Generating next alert")
                continue
            time.sleep(10)
