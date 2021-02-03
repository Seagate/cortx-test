"""Script used to generate engineering csv report."""
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

import common


def get_component_breakup_from_testplan(test_plan: str, username: str, password: str):
    """Get component breakup from testplan."""
    te_keys = common.get_test_executions_from_test_plan(test_plan, username, password)
    te_keys = [te["key"] for te in te_keys]
    components = {}
    for test_execution in te_keys:
        tests = common.get_test_from_test_execution(test_execution, username, password)
        fail_count = sum(d['status'] == 'FAIL' for d in tests)
        pass_count = sum(d['status'] == 'PASS' for d in tests)
        total_count = len(tests)
        detail = common.get_issue_details(test_execution, username, password)
        component = detail['fields']['labels'][0]
        if component in components:
            components[component] = {
                'total': components[component]['total'] + total_count,
                'pass': components[component]['pass'] + pass_count,
                'fail': components[component]['fail'] + fail_count
            }
        else:
            components[component] = {'total': total_count, 'pass': pass_count, 'fail': fail_count}
    return components


def get_component_level_summary(test_plans: list, username: str, password: str):
    """Get component level summary from testplan."""
    component_summary = []
    builds = []
    for t_plan in test_plans:
        if t_plan:
            component_summary.append(
                get_component_breakup_from_testplan(t_plan, username, password)
            )
            builds.append(common.get_build_from_test_plan(t_plan, username, password))
        else:
            component_summary.append({})
            builds.append("NA")
    data = [
        ["Component Level Summary"],
        ["Component", "Total", builds[0], "", builds[1], "", builds[2], "", builds[3], ""],
        ["", "", "Pass", "Fail", "Pass", "Fail", "Pass", "Fail", "Pass", "Fail"],
    ]
    components = {key for comp in component_summary for key in comp}

    for component in components:
        row = [component]

        if component not in component_summary[0]:
            total = "NA"
        else:
            total = component_summary[0][component]["total"]
        row.append(total)

        for component_sum in component_summary:
            if component in component_sum:
                row.append(component_sum[component]["pass"])
                row.append(component_sum[component]["fail"])
            else:
                row.append("NA")
                row.append("NA")
        data.extend([row])
    return data


def get_single_bucket_perf_stats():
    """ToDo: Need to complete by taking help from performance team."""
    return [[]]


def get_multiple_bucket_perf_stats():
    """ToDo: Need to complete by taking help from performance team."""
    return [[]]


def get_metadata_latencies():
    """ToDo: Need to complete by taking help from performance team."""
    return [[]]


def get_test_ids_from_linked_issues(linked_issues):
    """
    Get test IDs from linked issues.
    Returns test IDs from linked issues dictionary.
    linked_issues = [
        {
            "type": {"name": "Defect", "inward": "created by"},
            "inwardIssue": {"key": "TEST-5342"}
        }, {}
    ]
    """
    tests = []
    for issue in linked_issues:
        if issue["type"]["name"] == "Defect" and issue["type"]["inward"] == "created by" and \
                issue["inwardIssue"]["key"].startswith("TEST-"):
            tests.append(issue["inwardIssue"]["key"])
    return tests


def get_detailed_reported_bugs(test_plan: str, username: str, password: str):
    """
    summary: Get detailed reported bugs from testplan.
    """
    defects = common.get_defects_from_test_plan(test_plan, username, password)
    data = [
        ["Detailed Reported Bugs"],
        ["Component", "Test ID", "Priority", "JIRA ID", "Status", "Description"],
    ]
    for defect_id in defects:
        defect_details = common.get_issue_details(defect_id, username, password)
        defect_details = defect_details["fields"]
        component = defect_details["components"][0]["name"]
        priority = defect_details["priority"]["name"]
        summary = defect_details["summary"]
        status = defect_details["status"]["name"]
        tests = get_test_ids_from_linked_issues(defect_details["issuelinks"])
        data.extend([[component, "/".join(tests), priority, defect_id, status, summary]])

    return data


def main():
    """Generate csv engineering report from test plan JIRA."""
    parser = argparse.ArgumentParser()
    parser.add_argument('tp', help='Testplan for current build')
    parser.add_argument('--tp1', help='Testplan for current-1 build', default=None)
    parser.add_argument('--tp2', help='Testplan for current-2 build', default=None)
    parser.add_argument('--tp3', help='Testplan for current-3 build', default=None)

    test_plans = parser.parse_args()

    username, password = common.get_username_password()
    main_table_data, build = common.get_main_table_data(test_plans.tp, username, password)
    report_bugs_table_data = common.get_reported_bug_table_data(test_plans.tp, username, password)
    overall_qa_table_data = common.get_overall_qa_report_table_data(test_plans.tp, test_plans.tp1,
                                                                    build, username,
                                                                    password)
    component_level_summary_data = get_component_level_summary(
        [test_plans.tp, test_plans.tp1, test_plans.tp2, test_plans.tp3], username, password
    )
    # single_bucket_perf_stats = get_single_bucket_perf_stats(build)
    # get_multiple_bucket_perf = get_multiple_bucket_perf_stats(build)
    # metadata_latencies = get_metadata_latencies(build)
    # timing_summary_table_data = common.get_timing_summary(build)
    detailed_reported_bugs = get_detailed_reported_bugs(test_plans.tp, username, password)

    data = []
    data.extend(main_table_data)
    data.extend([""])
    data.extend(report_bugs_table_data)
    data.extend([""])
    data.extend(overall_qa_table_data)
    data.extend([""])
    data.extend(component_level_summary_data)
    data.extend([""])
    data.extend(detailed_reported_bugs)
    with open("../engg_report.csv", "a", newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(data)


if __name__ == '__main__':
    main()
