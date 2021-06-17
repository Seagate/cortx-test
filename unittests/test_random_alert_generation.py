import time
import threading
import logging
from commons.alerts_simulator.random_alerts.random_alert_generation \
    import RandomAlerts
from config import CMN_CFG

LOGGER = logging.getLogger(__name__)


def test_random_alerts():
    t_end = time.time() + 20 * 15
    e = threading.Event()
    host = CMN_CFG["nodes"][0]["host"]
    uname = CMN_CFG["nodes"][0]["username"]
    passwd = CMN_CFG["nodes"][0]["password"]
    ra_obj = RandomAlerts(host=host, h_user=uname, h_pwd=passwd,
                          enclosure_ip=CMN_CFG["enclosure"]["primary_enclosure_ip"],
                          enclosure_user=CMN_CFG["enclosure"]["enclosure_user"],
                          enclosure_pwd=CMN_CFG["enclosure"]["enclosure_pwd"])

    thread = threading.Thread(target=ra_obj.generate_random_alerts, args=(e,))
    thread.daemon = True  # Daemonize thread
    thread.start()
    LOGGER.info("Current time: %s", time.time())
    while time.time() < t_end:
        LOGGER.info("RUNNING RANDOM ALERTS IN BACKGROUND")
        time.sleep(20)

    e.set()
    LOGGER.info("Event is set.")
    LOGGER.info("Waiting")
    thread.join()
