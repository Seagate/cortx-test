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
from config import CMN_CFG
from libs.di.data_generator import DataGenerator
from libs.di.di_feature_control import DIFeatureControl
from commons.constants import const


class DIErrorDetectionLib:
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

    def validate_default_config(self):
        """
        function will check for default configs
        and decide whether test should be skipped during execution or not
        function will return True if configs are not set with default
        and will return false if configs are set to default
        """
        skip_mark = True
        write_flag = self.di_control.verify_s3config_flag_enable_all_nodes(
            section=self.config_section, flag=self.write_param)
        read_flag = self.di_control.verify_s3config_flag_enable_all_nodes(
            section=self.config_section, flag=self.read_param)
        integrity_flag = self.di_control.verify_s3config_flag_enable_all_nodes(
            section=self.config_section, flag=self.integrity_param)
        if write_flag[0] and not read_flag[0] and integrity_flag[0]:
            skip_mark = False
        return skip_mark

    def validate_disabled_config(self):
        """
        function will check for disabled configs
        and decide whether test should be skipped during execution or not
        function will return True if configs are enabled
        will return false if configs are disabled
        """
        skip_mark = True
        write_flag = self.di_control.verify_s3config_flag_enable_all_nodes(
            section=self.config_section, flag=self.write_param)
        read_flag = self.di_control.verify_s3config_flag_enable_all_nodes(
            section=self.config_section, flag=self.read_param)
        integrity_flag = self.di_control.verify_s3config_flag_enable_all_nodes(
            section=self.config_section, flag=self.integrity_param)
        if write_flag[0] and read_flag[0] and integrity_flag[0]:
            skip_mark = True
        return skip_mark
