#!/usr/bin/python
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
