# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""Procpath memory stats collector """

import logging
import os.path
from datetime import datetime
from multiprocessing import Process

from commons.constants import PID_WATCH_LIST, REQUIRED_MODULES
from commons.helpers.pods_helper import LogicalNode
from commons.params import LOG_DIR_NAME, LATEST_LOG_FOLDER
from commons.commands import PROC_CMD


# check and set pytest logging level as Globals.LOG_LEVEL
LOGGER = logging.getLogger(__name__)


class EnableProcPathStatsCollection:

    def __init__(self, cmn_cfg):
        """Initialize connection to Nodes or Pods.
        :param cmn_cfg: Common config
        """
        self.cmn_cfg = cmn_cfg
        self.dst_log_folder = 'dst'
        self.log_path = os.path.join(LOG_DIR_NAME, LATEST_LOG_FOLDER, self.dst_log_folder)
        os.makedirs(self.log_path, exist_ok=True)
        self.nodes = cmn_cfg["nodes"]
        self.worker_node_list = list()
        self.worker_stat_files_dict = dict()
        for node in self.nodes:
            if node["node_type"].lower() == "worker":
                node_obj = LogicalNode(hostname=node["hostname"],
                                       username=node["username"],
                                       password=node["password"])
                self.worker_node_list.append(node_obj)
        self.stat_collection = []

    @staticmethod
    def exe_cmd(worker: LogicalNode, cmd: str):
        """function to execute command collection
        :param worker: Object of Logical node
        :param cmd: command to be executed on worker node
        """
        LOGGER.debug("executing procpath cmd for stat collection")
        worker.execute_cmd(cmd=cmd)

    @staticmethod
    def get_pids(worker, watch_list):
        """function to get pids
        :param worker: Logical node object
        :param watch_list: list of string to be used in grepping command
        """
        pid_dict = {}
        for proc in watch_list:
            res = worker.execute_cmd("echo $(pgrep {})".format(proc))
            LOGGER.info(f'{proc} PIDs {res}')
            pid_dict[proc] = res
        return pid_dict

    def collect_pids(self, worker_stat_files_dict: dict):
        """
        function to collect pids and write them to a file
        :param worker_stat_files_dict: dictionary containing filename and worker object
        """
        for file_name, worker in worker_stat_files_dict.items():
            pid_dict = self.get_pids(worker=worker, watch_list=PID_WATCH_LIST)
            file_path = os.path.join(self.log_path, worker.hostname)
            with open("{}".format(file_path), 'a') as fp:
                fp.write(f"\npids : {pid_dict} file_name : {file_name}\n")

    def setup_requirement(self):
        """Install required modules on worker nodes for procpath collection"""
        LOGGER.info("checking for installation required modules")
        for worker_node in self.worker_node_list:
            resp = worker_node.execute_cmd("pip list")
            LOGGER.debug(resp)
            for module in REQUIRED_MODULES:
                if module in str(resp):
                    LOGGER.info("already installed module {}".format(module))
                else:
                    retry = 0
                    while retry < 2:
                        try:
                            LOGGER.info("installing {}".format(module))
                            worker_node.execute_cmd("pip install {}".format(module))
                            break
                        except IOError as err:
                            LOGGER.info("facing error {} while installing {}".format(err, module))
                            LOGGER.info("retrying installation of {}".format(module))
                            retry += 1
                    if retry >= 2:
                        return False, "Installation of Procpath required modules failed."
        return True, "setup installation completed."

    def start_collection(self):
        """trigger command for collection stats"""
        LOGGER.debug("starting stat collection")
        for worker in self.worker_node_list:
            file_name = "{}_{}.sqlite".format(str(worker.hostname).replace('.colo.seagate.com', ''),
                                              str(datetime.now().strftime("%m_%d_%Y_%H_%M_%S")))
            self.worker_stat_files_dict[file_name] = worker
            self.stat_collection.append(Process(target=self.exe_cmd,
                                                args=(worker, PROC_CMD.format(file_name))))
        self.collect_pids(self.worker_stat_files_dict)
        for proc in self.stat_collection:
            proc.start()

    def stop_collection(self):
        """stop collection"""
        for proc in self.stat_collection:
            if proc.is_alive():
                proc.kill()
        for worker in self.worker_node_list:
            self.exe_cmd(worker, cmd="for each in `pgrep proc` ; do `kill $each` ; done")
        LOGGER.debug("stopping stat collection")

    def validate_collection(self):
        """validate collection
        check for sqlite files generated
        """
        LOGGER.debug("checking if stat collection is alive")
        for proc in self.stat_collection:
            if not proc.is_alive():
                return False, "process is not alive"
        for file_name, worker in self.worker_stat_files_dict.items():
            if not worker.path_exists(file_name):
                return False, "log files are missing"
        return True, "process and logs are being generated"

    def get_stat_files_to_local(self):
        """function to collect generated logs and copy them back to local"""
        file_paths = dict()
        for file_name, worker in self.worker_stat_files_dict.items():
            if not worker.path_exists(file_name):
                file_paths[worker] = "files are missing"
            else:
                file_path = os.path.join(self.log_path, file_name)
                resp = worker.copy_file_to_local(remote_path=file_name, local_path=file_path)
                LOGGER.info(resp)
                file_paths[worker] = file_path
        return True, file_paths
