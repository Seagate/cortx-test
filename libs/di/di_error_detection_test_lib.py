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
from config import CMN_CFG
from libs.di.data_generator import DataGenerator
from libs.di.di_feature_control import DIFeatureControl


LOGGER = logging.getLogger(__name__)


class DIErrorDetection:
    """
    class having lib methods for DI
    error detection
    """

    def __init__(self):
        self.data_gen = DataGenerator()
        self.di_control = DIFeatureControl(cmn_cfg=CMN_CFG)
        self.config_section = "S3_SERVER_CONFIG"
        self.write_param = const.S3_DI_WRITE_CHECK
        self.read_param = const.S3_DI_READ_CHECK
        self.integrity_param = const.S3_METADATA_CHECK

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

    def create_file(self, size, first_byte, name):
        """
        this function will create a corrupted file
        :param size: size of file
        :param first_byte: first byte of file 'z' , 'f'
        :param name: file path
        :return location of file
        """
        buff, csm = self.data_gen.generate(size=size,
                                           seed=self.data_gen.get_random_seed())
        if first_byte:
            buff = self.data_gen.add_first_byte_to_buffer(first_byte=first_byte, buffer=buff)
        self.data_gen.create_file_from_buf(fbuf=buff, name=name, size=size)

    def validate_default_config(self):
        """
        function will check for default configs
        and decide whether test should be skipped during execution or not
        function will return True if configs are not set with default
        and will return false if configs are set to default
        """
        return self.validate_valid_config(default_cfg=True)

    def validate_enabled_config(self):
        """
        function will check for enabled configs
        and decide whether test should be skipped during execution or not
        function will return True if configs are set with True for all
        and will return false if configs are set otherwise
        """
        return self.validate_valid_config(enabled_cfg=True)
    
    def validate_disabled_config(self):
        """
        function will check for disabled configs
        and decide whether test should be skipped during execution or not
        function will return True if configs are set with False for all
        and will return False if configs are set otherwise
        """
        return self.validate_valid_config(disabled_cfg=True)


    def validate_valid_config(self, default_cfg: bool = False, 
                            enabled_cfg: bool = False,
                            disabled_cfg: bool = False):
        """
        This function needs optimization.
        :param: default_cfg Boolean
        :param: enabled_cfg Boolean
        :return:tuple
        """
        skip_mark = True
        resp = self.di_control.verify_s3config_flag_all_nodes(section=self.config_section,
                                                              flag=self.write_param)
        LOGGER.debug("%s resp : %s", self.write_param, resp)
        if resp[0]:
            write_flag = resp[1]
        else:
            return False, resp[1]
        resp = self.di_control.verify_s3config_flag_all_nodes(section=self.config_section,
                                                              flag=self.read_param)
        LOGGER.debug("%s resp : %s", self.read_param, resp)
        if resp[0]:
            read_flag = resp[1]
        else:
            return False, resp[1]
        resp = self.di_control.verify_s3config_flag_all_nodes(section=self.config_section,
                                                              flag=self.integrity_param)
        LOGGER.debug("%s resp : %s", self.integrity_param, resp)
        if resp[0]:
            integrity_flag = resp[1]
        else:
            return False, resp[1]
        if default_cfg:
            if write_flag and not read_flag and integrity_flag:
                skip_mark = False
        elif enabled_cfg:
            if write_flag and read_flag and integrity_flag:
                    skip_mark = False
        elif disabled_cfg:
            if not write_flag and not read_flag and not integrity_flag:
                    skip_mark = False
        else:
            if write_flag and integrity_flag:
                    skip_mark = False
        return True, skip_mark