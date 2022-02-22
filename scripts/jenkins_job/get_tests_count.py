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
Tests count from test plan
"""

import argparse
import csv
import os
from commons.utils import jira_utils

# CSV file contain test count in sequence[total,passed,fail,skip,todo]
TOTAL_COUNT_CSV = 'total_count.csv'


def main():
    """
    main function
    """
    parser = argparse.ArgumentParser(description="TODO count")
    parser.add_argument("-tp", help="test plan", required=True)
    parser.add_argument("-ji", help="jira password", required=True)
    parser.add_argument("-jp", help="jira id", required=True)
    args = parser.parse_args()
    test_plan_id = args.tp
    jira_password = args.jp
    jira_id = args.ji
    res = jira_utils.JiraTask.get_test_list_from_test_plan(test_plan_id, jira_id, jira_password)
    total = len(res)
    todo = len([test for test in res if test['latestStatus'] == 'TODO'])
    passed = len([test for test in res if test['latestStatus'] == 'PASS'])
    fail = len([test for test in res if test['latestStatus'] == 'FAIL'])
    skip = len([test for test in res if test['latestStatus'] == 'SKIPPED'])
    with open(os.path.join(os.getcwd(), TOTAL_COUNT_CSV), 'w', newline='') as tp_info_csv:
        writer = csv.writer(tp_info_csv)
        writer.writerow([total, passed, fail, skip, todo])


if __name__ == "__main__":
    main()
