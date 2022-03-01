#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# 
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
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
