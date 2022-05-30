#!/usr/bin/python
# -*- coding: utf-8 -*-
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
    skip = len([test for test in res if test['latestStatus'] in ['SKIPPED', 'BLOCKED']])
    exe = len([test for test in res if test['latestStatus'] == 'EXECUTING'])
    with open(os.path.join(os.getcwd(), TOTAL_COUNT_CSV), 'w', newline='') as tp_info_csv:
        writer = csv.writer(tp_info_csv)
        writer.writerow([total, passed, fail, skip, todo, exe])


if __name__ == "__main__":
    main()
