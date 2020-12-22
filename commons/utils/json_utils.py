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

import os
import json


def create_content_json(home, data, user_json):
    """

    :param home:
    :param data:
    :param user_json:
    :return:
    """
    pth = os.path.join(home, user_json)
    with open(pth, 'w') as outfile:
        json.dump(data, outfile, ensure_ascii=False)


def read_content_json(home, user_json):
    """

    :param home:
    :param user_json:
    :return:
    """
    pth = os.path.join(home, user_json)
    data = None
    with open(pth, 'rb') as json_file:
        data = json.loads(json_file.read())
    return data

