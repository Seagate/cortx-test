#!/usr/bin/env python3
# pylint: disable=import-error

# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.


"""
Module helps in generating the mock health event and publishing it to the message bus.
It is provided by HA. If any changes are done by HA Dev team, this needs to be
copied from cortx-ha/ha/util/health_generator/mock_health_event_publisher.py
"""


import argparse
import sys
import pathlib
import errno
import json
import time

from cortx.utils.conf_store import Conf
from cortx.utils.event_framework.health import HealthAttr, HealthEvent
from ha.util.conf_store import ConftStoreSearch
from ha.core.config.config_manager import ConfigManager
from ha import const
from ha.util.message_bus import MessageBus
from ha.core.system_health.const import HEALTH_STATUSES

DOCKER_ENV_FILE = '/.dockerenv'
_INDEX = 'cortx'
CLUSTER_CONFIG_FILE = '/etc/cortx/cluster.conf'
CONFIG_FILE_FORMAT = 'yaml'
_EVENTS_KEY = 'events'
_SOURCE_KEY = 'source'
_NODE_ID_KEY = 'node_id'
_RESOURCE_TYPE_KEY = 'resource_type'
_RESOURCE_ID_KEY = 'resource_id'
_RESOURCE_STATUS_KEY = 'resource_status'
_SPECIFIC_INFO_KEY = 'specific_info'
_DELAY_KEY = 'delay'


def is_container_env() -> bool:
    """Returns True if environment is docker container else False."""
    docker_env_file_path = pathlib.Path(DOCKER_ENV_FILE)
    if docker_env_file_path.exists():
        return True
    return False


# pylint: disable=redefined-outer-name
def get_data_nodes() -> list:
    """
    Fetches data node ids using HA wrapper class and displays the result.

    Args:
    conf_store: ConftStoreSearch object

    Returns: list of node ids
    """
    data_node_ids = ConftStoreSearch.get_data_pods(_INDEX)
    return data_node_ids


def get_server_nodes() -> list:
    """
    Fetches server node ids using HA wrapper class and displays the result.

    Args:
    conf_store: ConftStoreSearch object

    Returns: list of node ids
    """
    server_node_ids = ConftStoreSearch.get_server_pods(_INDEX)
    return server_node_ids


# pylint: disable=redefined-outer-name
def get_disks(args: argparse.Namespace) -> None:
    """
    Fetches disk ids using ConfStore search API and displays the result.

    Args:
    conf_store: ConftStoreSearch object
    node_id: machine_id value
    """
    disk_ids = ConftStoreSearch.get_disk_list(_INDEX, args.node_id)
    print(disk_ids)


# pylint: disable=redefined-outer-name
def get_cvgs(args: argparse.Namespace) -> None:
    """
    Fetches cvg ids using ConfStore search API and displays the result.

    Args:
    conf_store: ConftStoreSearch object
    node_id: machine_id value
    """
    cvg_ids = ConftStoreSearch.get_cvg_list(_INDEX, args.node_id)
    print(cvg_ids)


# pylint: disable=too-many-locals, redefined-outer-name, broad-except, unspecified-encoding
# pylint: disable=protected-access, inconsistent-return-statements
def publish(args: argparse.Namespace) -> None:
    """
    publishes the message on the message bus.

    Args:
    args: parsed argument
    conf_store: ConftStoreSearch object
    """
    try:
        with open(args.file, 'r') as fi_p:
            events_dict = json.load(fi_p)
            if _EVENTS_KEY in events_dict.keys():
                ConfigManager.init(None)
                MessageBus.init()
                message_type = Conf.get(const.HA_GLOBAL_INDEX,
                                        f'FAULT_TOLERANCE{const._DELIM}message_type')
                message_producer = MessageBus.get_producer("health_event_generator", message_type)
                cluster_id = Conf.get(const.HA_GLOBAL_INDEX,
                                      f'COMMON_CONFIG{const._DELIM}cluster_id')
                site_id = Conf.get(const.HA_GLOBAL_INDEX, f'COMMON_CONFIG{const._DELIM}site_id')
                rack_id = Conf.get(const.HA_GLOBAL_INDEX, f'COMMON_CONFIG{const._DELIM}rack_id')
                # TODO: Read from config when available.  # pylint: disable=fixme
                storageset_id = '1'
                for _, value in events_dict[_EVENTS_KEY].items():
                    resource_type = value[_RESOURCE_TYPE_KEY]
                    resource_type_list = Conf.get(const.HA_GLOBAL_INDEX,
                                                  f"CLUSTER{const._DELIM}resource_type")
                    if resource_type not in resource_type_list:
                        raise Exception(f'Invalid resource_type: {resource_type}')
                    resource_status = value[_RESOURCE_STATUS_KEY]
                    status_supported = False
                    for status in list(HEALTH_STATUSES):
                        if resource_status == status.value:
                            status_supported = True
                            break
                    if status_supported is False:
                        raise Exception(f'Invalid resource_status: {resource_status}')
                    payload = {
                        f'{HealthAttr.SOURCE}': value[_SOURCE_KEY],
                        f'{HealthAttr.CLUSTER_ID}': cluster_id,
                        f'{HealthAttr.SITE_ID}': site_id,
                        f'{HealthAttr.RACK_ID}': rack_id,
                        f'{HealthAttr.STORAGESET_ID}': storageset_id,
                        f'{HealthAttr.NODE_ID}': value[_NODE_ID_KEY],
                        f'{HealthAttr.RESOURCE_TYPE}': resource_type,
                        f'{HealthAttr.RESOURCE_ID}': value[_RESOURCE_ID_KEY],
                        f'{HealthAttr.RESOURCE_STATUS}': resource_status
                    }
                    health_event = HealthEvent(**payload)
                    health_event.set_specific_info(value[_SPECIFIC_INFO_KEY])
                    print(f"Publishing health event {health_event.json}")
                    message_producer.publish(health_event.json)
                    if _DELAY_KEY in events_dict.keys():
                        print(f"Sleeping for {events_dict[_DELAY_KEY]} seconds")
                        time.sleep(events_dict[_DELAY_KEY])
    except Exception as err:
        sys.stderr.write(f"Health event generator failed. Error: {err}\n")
        return errno.EINVAL


FUNCTION_MAP = {
                '-gdt': get_data_nodes, '--get-data-nodes': get_data_nodes,
                '-gs': get_server_nodes, '--get-server-nodes': get_server_nodes
                }


def get_args() -> (argparse.Namespace, argparse.ArgumentParser):
    """
    Configures the command line arguments.

    Returns:
    args: parsed argument object
    my_parser: Parser object
    """
    my_parser = argparse.ArgumentParser(prog='health_event_publisher',
                                        usage='%(prog)s [options]',
                                        description='Helps in publishing the mock health event',
                                        epilog='Hope it is useful! :)')

    subparsers = my_parser.add_subparsers()

    my_parser.add_argument('-gdt', '--get-data-nodes', action='store_true',
                           help='Get the list of data node ids')
    my_parser.add_argument('-gs', '--get-server-nodes', action='store_true',
                           help='Get the list of server node ids')

    parser_publish = subparsers.add_parser('publish', help='Publish the message')
    parser_publish.add_argument('-f', '--file', action='store', help='input config file',
                                required=True)
    parser_publish.set_defaults(handler=publish)

    parser_disks = subparsers.add_parser('get-disks',
                                         help='Displays the Disk Ids associated with the Node')
    parser_disks.add_argument('-n', '--node-id', help='Node id for which disk id is required',
                              required=True)
    parser_disks.set_defaults(handler=get_disks)

    parser_cvgs = subparsers.add_parser('get-cvgs',
                                        help='Displays the CVG Ids associated with the Node')
    parser_cvgs.add_argument('-n', '--node-id', help='Node id for which cvg id is required',
                             required=True)
    parser_cvgs.set_defaults(handler=get_cvgs)

    args = my_parser.parse_args()
    return args, my_parser


if __name__ == '__main__':
    if not is_container_env():
        sys.exit('Please use this script in containerized environment')
    OPTION = None
    args, parser_obj = get_args()
    Conf.init()
    file_to_load = f'{CONFIG_FILE_FORMAT}://{CLUSTER_CONFIG_FILE}'
    Conf.load(_INDEX, file_to_load)
    _conf_store = ConftStoreSearch(conf_store_req=False)

    data_node_ids = get_data_nodes()

    if len(sys.argv) > 1:
        OPTION = sys.argv[1]
    else:
        parser_obj.print_help()
        sys.exit(0)

    if hasattr(args, 'handler'):
        if hasattr(args, 'node_id') and args.node_id not in data_node_ids:
            print(f'Required data is not supported for given node_id: {args.node_id}. \
                    Please check supported node ids list: {data_node_ids}')
            sys.exit(1)
        args.handler(args)
    else:
        print(FUNCTION_MAP[OPTION]())
