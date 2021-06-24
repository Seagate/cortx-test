#!/usr/bin/python
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

"""
Provisioner utiltiy methods
"""
import shutil
import logging
import time
import re
from commons import constants as common_cnst
from commons import commands as common_cmd
from commons import params as prm
from commons import pswdmanager
from commons.utils import config_utils


LOGGER = logging.getLogger(__name__)


class ProvSWUpgrade:
    """
    This class contains utility methods for all the operations related
    to SW upgrade processes.
    """

    @staticmethod
    def set_validate_repo(iso_list: str):
        """
        Setting the SW upgrade repo and validating it if set to desired build
        """