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
CLONED_TE_CSV = 'cloned_tp_info.csv'
TESTS_TE_CSV = 'te_tests_count.csv'

# pylint:disable=too-many-locals
def get_te_test_count(te_dict, jobject):
    """
    Get test count from TE
    :param te_dict: Dictionary of TE
    :param jobject: Jira Object
    """
    with open(os.path.join(os.getcwd(), TESTS_TE_CSV), 'w', newline='', encoding="utf8") as te_csv:
        writer = csv.writer(te_csv)
        total_count = ['Total', 0, 0, 0, 0, 0, 0]
        for key, val in te_dict.items():
            total = todo = passed = fail = skip = exe = 0
            for test_exe_id in val:
                res = jobject.get_test_details(test_exe_id)
                for test in res:
                    res = test
                total += len(res)
                todo += len([test for test in res if test["status"] == 'TODO'])
                passed += len([test for test in res if test["status"] == 'PASS'])
                fail += len([test for test in res if test["status"] == 'FAIL'])
                skip += len([test for test in res if test["status"] in ['SKIPPED', 'BLOCKED']])
                exe += len([test for test in res if test["status"] == 'EXECUTING'])
            total_count[1] += total
            total_count[2] += passed
            total_count[3] += fail
            total_count[4] += skip
            total_count[5] += todo
            total_count[6] += exe
            writer.writerow([key, total, passed, fail, skip, todo, exe])
        writer.writerow(total_count)

def get_tp_test_count(test_plan, jira_id, jira_pass):
    """
    Get test count from TP
    :param test_plan: TP ID
    :param jira_id: Jira ID
    :param jira_pass: Jira Password
    """
    res = jira_utils.JiraTask.get_test_list_from_test_plan(test_plan, jira_id, jira_pass)
    total = len(res)
    todo = len([test for test in res if test['latestStatus'] == 'TODO'])
    passed = len([test for test in res if test['latestStatus'] == 'PASS'])
    fail = len([test for test in res if test['latestStatus'] == 'FAIL'])
    skip = len([test for test in res if test['latestStatus'] in ['SKIPPED', 'BLOCKED']])
    exe = len([test for test in res if test['latestStatus'] == 'EXECUTING'])
    with open(os.path.join(os.getcwd(), TOTAL_COUNT_CSV), 'w', newline='', encoding="utf8") as t_p:
        writer = csv.writer(t_p)
        writer.writerow([total, passed, fail, skip, todo, exe])


def main():
    """
    main function
    """
    parser = argparse.ArgumentParser(description="TODO count")
    parser.add_argument("-tp", help="test plan", required=False)
    parser.add_argument("-ji", help="jira password", required=True)
    parser.add_argument("-jp", help="jira id", required=True)
    args = parser.parse_args()
    test_plan_id = args.tp
    jira_password = args.jp
    jira_id = args.ji
    if test_plan_id:
        get_tp_test_count(test_plan_id, jira_id, jira_password)
    else:
        jobject = jira_utils.JiraTask(jira_id, jira_password)
        original_te = {"TEST-37458": "Sanity_TE", "TEST-39283": "Data_Path_TE",
                       "TEST-40061": "Failure_TE"}
        dict_te = {"Sanity_TE": [], "Data_Path_TE": [], "Failure_TE": [], "Regre_TE": []}
        with open(os.path.join(os.getcwd(), CLONED_TE_CSV), 'r', encoding="utf8") as file:
            csvreader = csv.reader(file)
            for row in csvreader:
                if row[2] in original_te:
                    k = original_te[row[2]]
                    dict_te[k].append(row[1])
                else:
                    dict_te["Regre_TE"].append(row[1])
        get_te_test_count(dict_te, jobject)

if __name__ == "__main__":
    main()
