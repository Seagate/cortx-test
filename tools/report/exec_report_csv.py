"""Script used to generate executive csv report."""
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
import argparse
import csv
from collections import Counter

from jira import JIRA

import jira_api


def prepare_feature_data(total_count, pass_count, fail_count):
    """Create feature summary data."""
    data = [["Feature Breakdown Summary"],
            ["Features", "Total", "Pass", "Failed", "% Pass", "% Failed"]]

    for feature in total_count:
        f_pass = pass_count[feature]
        f_total = total_count[feature]
        f_fail = fail_count[feature]
        if f_total:
            pct_pass = f_pass * 100 / f_total
            pct_fail = f_fail * 100 / f_total
        else:
            pct_pass = 0
            pct_fail = 0
        data.extend([[feature, f_total, f_pass, f_fail, "%.2f" % pct_pass, "%.2f" % pct_fail]])

    return data


def get_feature_breakdown_summary_table_data(test_plan: str, username: str, password: str):
    """Get feature breakdown summary table data."""
    fail_count = {}
    pass_count = {}
    total_count = {}
    jira_url = 'https://jts.seagate.com/'
    options = {'server': jira_url}
    jira = JIRA(options, basic_auth=(username, password))
    for feature in jira_api.FEATURES:
        fail_count[feature] = jira.search_issues(
            f'issue in testPlanFolderTests({test_plan},\'{feature}\',\'true\',\'FAIL\',\'\')',
            maxResults=500, json_result=True)["total"]
        pass_count[feature] = jira.search_issues(
            f'issue in testPlanFolderTests({test_plan},\'{feature}\',\'true\',\'PASS\',\'\')',
            maxResults=500, json_result=True)["total"]
        total_count[feature] = jira.search_issues(
            f'issue in testPlanFolderTests({test_plan},\'{feature}\',\'true\')',
            maxResults=500, json_result=True)["total"]

    total_non_orphans = sum(total_count.values())
    total_pass_non_orphans = sum(pass_count.values())
    total_fail_non_orphans = sum(fail_count.values())

    total_count["Total"] = len(jira_api.get_test_list_from_test_plan(test_plan, username, password))
    pass_count["Total"] = sum(
        x.get('latestStatus') == "PASS" for x in
        jira_api.get_test_list_from_test_plan(test_plan, username, password))
    fail_count["Total"] = sum(
        x.get('latestStatus') == "FAIL" for x in
        jira_api.get_test_list_from_test_plan(test_plan, username, password))

    total_count["Orphans"] = total_count["Total"] - total_non_orphans
    pass_count["Orphans"] = pass_count["Total"] - total_pass_non_orphans
    fail_count["Orphans"] = fail_count["Total"] - total_fail_non_orphans

    return prepare_feature_data(total_count, pass_count, fail_count)


def get_code_maturity_data(test_plan: str, test_plan1: str, test_plan2: str,
                           username: str, password: str):
    """Get code maturity data."""
    counters = []
    builds = []
    for t_plan in [test_plan, test_plan1, test_plan2]:
        if t_plan:
            tests = jira_api.get_test_list_from_test_plan(test_plan, username, password)
            counters.append(Counter(test['latestStatus'] for test in tests))
            builds.append(jira_api.get_build_from_test_plan(t_plan, username, password))
        else:
            counters.append(Counter())
            builds.append("NA")

    data = [
        ["Code Maturity"], ["", builds[0], builds[1], builds[2]],
        ["Total", sum(counters[0].values()), sum(counters[1].values()), sum(counters[2].values())],
    ]
    for status in jira_api.TEST_STATUS:
        data.append(
            [status.capitalize(), counters[0][status], counters[1][status], counters[2][status]]
        )
    return data


def get_single_bucket_perf_data():
    """ToDo: Need to complete this by taking help from performance team."""
    data = [
        ["Single Bucket Performance Statistics (Average) using S3Bench - in a Nutshell"],
        ["Statistics", "4 KB Object", "256 MB Object"],
        ["Write Throughput(MBps)", "92", "9"],
        ["Read Throughput(MBps)", "92", "9"],
        ["Write Latency(ms)", "92", "9"],
        ["Read Latency(ms)", "92", "9"]
    ]
    return data


def main():
    """Generate csv executive report from test plan JIRA."""
    parser = argparse.ArgumentParser()
    parser.add_argument('tp', help='Testplan for current build')
    parser.add_argument('--tp1', help='Testplan for current-1 build', default=None)
    parser.add_argument('--tp2', help='Testplan for current-2 build', default=None)

    test_plans = parser.parse_args()

    username, password = jira_api.get_username_password()
    main_table_data, build = jira_api.get_main_table_data(test_plans.tp, username, password)
    report_bugs_table_data = jira_api.get_reported_bug_table_data(test_plans.tp, username, password)
    overall_qa_table_data = jira_api.get_overall_qa_report_table_data(test_plans.tp, test_plans.tp1,
                                                                      build, username, password)
    feature_breakdown_summary_table_data = get_feature_breakdown_summary_table_data(
        test_plans.tp, username, password)
    code_maturity_table_data = get_code_maturity_data(test_plans.tp, test_plans.tp1, test_plans.tp2,
                                                      username, password)
    # single_bucket_perf_table_data = get_single_bucket_perf_data(build)
    timing_summary_table_data = jira_api.get_timing_summary()

    data = []
    data.extend(main_table_data)
    data.extend([""])
    data.extend(report_bugs_table_data)
    data.extend([""])
    data.extend(overall_qa_table_data)
    data.extend([""])
    data.extend(feature_breakdown_summary_table_data)
    data.extend([""])
    data.extend(code_maturity_table_data)
    data.extend([""])
    # data.extend(single_bucket_perf_table_data)
    # data.extend([""])
    data.extend(timing_summary_table_data)
    data.extend([""])
    with open("../exec_report.csv", "a", newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(data)


if __name__ == '__main__':
    main()
