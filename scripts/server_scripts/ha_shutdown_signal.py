#!/usr/bin/python
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

from cortx.utils.conf_store import Conf
from ha import const
from ha.util.message_bus import MessageBus
from ha.core.config.config_manager import ConfigManager
ConfigManager.init("test_Cluster_stop_sigterm")
confstore = ConfigManager.get_confstore()
MessageBus.init()
producer_id="csm_producer"
message_type = Conf.get(const.HA_GLOBAL_INDEX, f'CLUSTER_STOP_MON{const._DELIM}message_type')
producer = MessageBus.get_producer(producer_id=producer_id, message_type=message_type)
producer.publish({"start_cluster_shutdown":1})
