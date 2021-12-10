# !/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""
Python module to maintain all data error detection (F-23B) tests libraries.
These are top level functions and classes used by test classes.
"""
import logging

from commons.constants import const
from commons.helpers.pods_helper import LogicalNode
from commons.utils import system_utils
from config import CMN_CFG
from libs.di.data_generator import DataGenerator
from libs.di.di_feature_control import DIFeatureControl
from libs.di.fi_adapter import S3FailureInjection
LOGGER = logging.getLogger(__name__)


class DIErrorDetection:
    """
    class having lib methods for DI
    error detection
    """

    def __init__(self):
        self.data_gen = DataGenerator()
        self.di_control = DIFeatureControl(cmn_cfg=CMN_CFG)
        self.fi_adapter = S3FailureInjection(cmn_cfg=CMN_CFG)
        self.config_section = "S3_SERVER_CONFIG"
        self.write_param = const.S3_DI_WRITE_CHECK
        self.read_param = const.S3_DI_READ_CHECK
        self.integrity_param = const.S3_METADATA_CHECK
        self.master_node_list = []
        self.nodes = CMN_CFG["nodes"]
        for node in self.nodes:
            if node["node_type"].lower() == "master":
                node_obj = LogicalNode(hostname=node["hostname"],
                                       username=node["username"],
                                       password=node["password"])
                self.master_node_list.append(node_obj)

    def create_corrupted_file(self, size, first_byte, data_folder_prefix):
        """
        this function will create a corrupted file
        :param size: size of file
        :param first_byte: first byte of file
        :param data_folder_prefix: data folder prefix
        :return location of file
        """
        buff, csm = self.data_gen.generate(size=size,
                                           seed=self.data_gen.get_random_seed())
        buff = self.data_gen.add_first_byte_to_buffer(first_byte=first_byte, buffer=buff)
        location = self.data_gen.save_buf_to_file(fbuf=buff, csum=csm, size=size,
                                                  data_folder_prefix=data_folder_prefix)
        return location

    def validate_default_config(self):
        """
        function will check for default configs
        and decide whether test should be skipped during execution or not
        function will return True if configs are not set with default
        and will return false if configs are set to default
        """
        skip_mark = True
        resp = self.di_control.verify_s3config_flag_all_nodes(section=self.config_section,
                                                              flag=self.write_param,
                                                              master_node=self.master_node_list[0])
        LOGGER.debug("%s resp : %s", self.write_param, resp)
        if resp[0]:
            write_flag = resp[1]
        else:
            return False, resp[1]

        resp = self.di_control.verify_s3config_flag_all_nodes(section=self.config_section,
                                                              flag=self.read_param,
                                                              master_node=self.master_node_list[0])
        LOGGER.debug("%s resp : %s", self.read_param, resp)
        if resp[0]:
            read_flag = resp[1]
        else:
            return False, resp[1]

        resp = self.di_control.verify_s3config_flag_all_nodes(section=self.config_section,
                                                              flag=self.integrity_param,
                                                              master_node=self.master_node_list[0])
        LOGGER.debug("%s resp : %s", self.integrity_param, resp)
        if resp[0]:
            integrity_flag = resp[1]
        else:
            return False, resp[1]

        if write_flag and not read_flag and integrity_flag:
            skip_mark = False
        return True, skip_mark

    def validate_disabled_config(self):
        """
        function will check for disabled configs
        and decide whether test should be skipped during execution or not
        function will return True if configs are enabled
        will return false if configs are disabled
        """
        skip_mark = True
        resp = self.di_control.verify_s3config_flag_all_nodes(section=self.config_section,
                                                              flag=self.write_param,
                                                              master_node=self.master_node_list[0])
        LOGGER.debug("%s resp : %s", self.write_param, resp)
        if resp[0]:
            write_flag = resp[1]
        else:
            return False, resp[1]

        resp = self.di_control.verify_s3config_flag_all_nodes(section=self.config_section,
                                                              flag=self.read_param,
                                                              master_node=self.master_node_list[0])
        LOGGER.debug("%s resp : %s", self.read_param, resp)
        if resp[0]:
            read_flag = resp[1]
        else:
            return False, resp[1]

        resp = self.di_control.verify_s3config_flag_all_nodes(section=self.config_section,
                                                              flag=self.integrity_param,
                                                              master_node=self.master_node_list[0])
        LOGGER.debug("%s resp : %s", self.integrity_param, resp)
        if resp[0]:
            integrity_flag = resp[1]
        else:
            return False, resp[1]

        if not write_flag and not read_flag and not integrity_flag:
            skip_mark = False

        return True, skip_mark

    def get_file_and_csum(self, size, data_folder_prefix):
        """
        this function will create a corrupted file
        :param size: size of file
        :param data_folder_prefix: data folder prefix
        :return location of file
        """
        buff, csum = self.data_gen.generate(size=size, seed=self.data_gen.get_random_seed())
        location = self.data_gen.save_buf_to_file(fbuf=buff, csum=csum, size=size,
                                                  data_folder_prefix=data_folder_prefix)
        csm = system_utils.calculate_checksum(file_path=location, filter_resp=True)
        return location, csm

    def enable_data_corruption_set_fault_injection(self):
        fault_status = self.fi_adapter.set_fault_injection(flag=True)
        if fault_status[0]:
            LOGGER.debug("Step 2: fault injection set")
            status = self.fi_adapter.enable_data_block_corruption()
            if status:
                LOGGER.debug("Step 2: enabled data corruption")
                return True
            else:
                LOGGER.debug("Step 2: failed to enable data corruption")
        else:
            LOGGER.debug("Step 2: failed to set fault injection. Reason: %s", fault_status[1])
        return False

    def disable_data_corruption_set_fault_injection(self):
        fault_status = self.fi_adapter.set_fault_injection(flag=False)
        if fault_status[0]:
            LOGGER.debug("Step 2: fault injection unset")
            return True
        else:
            LOGGER.debug("Step 2: failed to set fault injection. Reason: %s", fault_status[1])
        return False
