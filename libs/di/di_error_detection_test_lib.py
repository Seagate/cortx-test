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

from libs.di.data_generator import DataGenerator


class DIErrorDetectionLib:
    """
    class having lib methods for DI
    error detection
    """
    def __init__(self):
        self.data_gen = DataGenerator()

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
