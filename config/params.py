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
# -*- coding: utf-8 -*-
# !/usr/bin/python
import os


LOG_FILE = 'cortx-test.log'

USER_JSON = '_usersdata'

CONFIG_DIR = 'config'

COMMON_CONFIG = os.path.join(CONFIG_DIR, 'common_config.yaml')

LOG_DIR_NAME = 'log'

JIRA_TEST_LIST = 'test_lists.csv'

JIRA_SELECTED_TESTS = 'selected_test_lists.csv'

JIRA_DIST_TEST_LIST = 'dist_test_lists.csv'