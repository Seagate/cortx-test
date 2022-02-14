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
Fetch result summary from TEST PLAN in JIRA.
"""
import os
import sys
from collections import Counter
from commons.utils import jira_utils


def main():
    """
    Main Function.
    """
    try:
        tp_no = os.getenv("TEST_PLAN_NUMBER", None)
        if tp_no is not None:
            jira_id = os.environ['JIRA_ID']
            jira_password = os.environ['JIRA_PASSWORD']
            counters = []
            tests = jira_utils.JiraTask.get_test_list_from_test_plan(tp_no, jira_id, jira_password)
            counters.append(Counter(test['latestStatus'] for test in tests))
            result_dict = counters[0]
            for key, value in result_dict.items():
                print(key, ":", value)
                with open("test_result.txt", 'a') as file:
                    file.write(key + ":" + str(value))
                    file.write("\n")
                    if key == "FAIL" and value != "0":
                        return False
    except Exception as ex:
        print(f"Exception Occurred : {ex}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
