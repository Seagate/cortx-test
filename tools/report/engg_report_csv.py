# -*- coding: utf-8 -*-
"""Script used to generate engineering csv report."""
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


import csv
from collections import defaultdict
from copy import deepcopy

import common
import jira_api
import mongodb_api

OPERATIONS = ["write", "read"]
STATS = ["Throughput", "Latency", "IOPS"]
CONFIG = [[1, 100], [10, 100], [50, 100]]
OBJECTS_SIZES = ["4Kb", "256Kb", "100Kb", "1Mb", "5Mb", "16Mb", "36Mb", "64Mb", "128Mb", "256Mb"]


def get_component_issue_summary_from_testplan(test_plan: str, username: str, password: str) -> dict:
    """
    Get component defect counts for given test plan.

    Returns: {"Automation": 4, "CSM": 2, "CFT": 0 ...}
    """
    te_keys = jira_api.get_test_executions_from_test_plan(test_plan, username, password)
    te_keys = [te_key["key"] for te_key in te_keys]
    component_defects = {component: 0 for component in common.COMPONENT_LIST}
    for test_execution in te_keys:
        tests = jira_api.get_test_from_test_execution(test_execution, username, password)
        defects = [defect["key"] for test in tests for defect in test["defects"]]
        for defect in defects:
            defect_details = jira_api.get_issue_details(defect, username, password)
            for component in defect_details.fields.components:
                if component.name in component_defects:
                    component_defects[component.name] += 1
    return component_defects


def get_component_issue_summary(test_plans: list, username: str, password: str):
    """Get component issue summary from testplan."""
    component_summary = {}
    builds = []
    component_summary["NA"] = {component: "-" for component in common.COMPONENT_LIST}
    for t_plan in test_plans:
        if t_plan:
            build = jira_api.get_details_from_test_plan(t_plan, username, password)["buildNo"]
            component_summary[build] = get_component_issue_summary_from_testplan(t_plan,
                                                                                 username,
                                                                                 password)
            builds.append(build)
        else:
            builds.append("NA")
    data = [
        ["Component Level Bugs Summary"],
        ["Component", builds[0], builds[1], builds[2], builds[3]],
    ]
    for component in common.COMPONENT_LIST:
        data.append([component.lstrip(), component_summary[builds[0]][component],
                     component_summary[builds[1]][component],
                     component_summary[builds[2]][component],
                     component_summary[builds[3]][component]])
    return data


def get_single_bucket_perf_stats(build, branch, uri, db_name, db_collection):
    """Get single bucket performance data for engineering report"""
    row_2 = deepcopy(OBJECTS_SIZES)
    row_2.insert(0, "Statistics")
    data = [["Single Bucket Performance Statistics (Average) using S3Bench"], row_2]
    operations = ["Write", "Read"]
    stats = ["Throughput", "Latency", "IOPS", "TTFB"]
    for operation in operations:
        for stat in stats:
            if stat in ["Latency", "TTFB"]:
                temp_data = [f"{operation} {stat} (ms)"]
            elif stat in ["Throughput"]:
                temp_data = [f"{operation} {stat} (MBps)"]
            else:
                temp_data = [f"{operation} {stat}"]
            for obj_size in OBJECTS_SIZES:
                query = {'Branch': branch, 'Build': build, 'Operation': operation,
                         'Object_Size': obj_size}
                count = mongodb_api.count_documents(query=query, uri=uri, db_name=db_name,
                                                    collection=db_collection)
                db_data = mongodb_api.find_documents(query=query, uri=uri, db_name=db_name,
                                                     collection=db_collection)
                if stat in ["Latency", "TTFB"]:
                    if count > 0 and common.keys_exists(db_data[0], stat, "Avg"):
                        temp_data.append(common.round_off(db_data[0][stat]["Avg"] * 1000))
                    else:
                        temp_data.append("-")
                else:
                    if count > 0 and common.keys_exists(db_data[0], stat)\
                            and "Count_of_Servers" in db_data[0]:
                        temp_data.append(
                            common.round_off(db_data[0][stat] / db_data[0]["Count_of_Servers"]))
                    else:
                        temp_data.append("-")
            data.extend([temp_data])
    return data


def get_bench_data(build, uri, db_name, db_collection, branch):
    """Read Hsbench data from DB"""
    data = []
    for tool in ["Hsbench", "Cosbench"]:
        for configs in CONFIG:
            row_num = 0
            for operation in OPERATIONS:
                for stat in STATS:
                    row_num += 1
                    head = ""
                    if row_num == 2:
                        head = tool
                    elif row_num == 3:
                        head = f"{configs[0]} Buckets"
                    elif row_num == 4:
                        head = f"{configs[1]} Sessions"
                    temp_data = [head, f"{operation.capitalize()} {stat}"]
                    for obj_size in OBJECTS_SIZES:
                        query = {'Build': build, 'Name': tool, 'Operation': operation,
                                 'Object_Size': obj_size, 'Buckets': configs[0],
                                 'Sessions': configs[1], "Branch": branch}
                        count = mongodb_api.count_documents(query=query, uri=uri, db_name=db_name,
                                                            collection=db_collection)
                        db_data = mongodb_api.find_documents(query=query, uri=uri, db_name=db_name,
                                                             collection=db_collection)

                        if count > 0 and stat == "Throughput" and common.keys_exists(db_data[0],
                                                                                     stat):
                            temp_data.append(
                                common.round_off(db_data[0][stat] / db_data[0]["Count_of_Servers"]))
                        elif count > 0 and common.keys_exists(db_data[0], stat):
                            temp_data.append(common.round_off(db_data[0][stat]))
                        else:
                            temp_data.append("-")
                    data.append(temp_data)
    return data


def get_multiple_bucket_perf_stats(build, branch, uri, db_name, db_collection):
    """Get multiple bucket performance data"""
    row_2 = deepcopy(OBJECTS_SIZES)
    row_2.insert(0, "Statistics")
    row_2.insert(0, "Tool")
    data = [["Multiple Buckets Performance Statistics (Average) using HSBench and COSBench"],
            row_2]

    data.extend(get_bench_data(build, uri, db_name, db_collection, branch))
    return data


def get_metadata_latencies(build, uri, db_name, db_collection):
    """Get metadata latency table data."""
    operations = ["PutObjTag", "GetObjTag", "HeadObj"]
    heading = ["Add / Edit Object Tags", "Read Object Tags", "Read Object Metadata"]
    data = [["Metadata Latencies (captured with 1KB object)"],
            ["Operation Latency (ms)", "Response Time"]]
    for ops, head in zip(operations, heading):
        query = {'Name': 'S3bench', 'Build': build, 'Object_Size': '1Kb', 'Operation': ops}
        count = mongodb_api.count_documents(query=query, uri=uri, db_name=db_name,
                                            collection=db_collection)
        db_data = mongodb_api.find_documents(query=query, uri=uri, db_name=db_name,
                                             collection=db_collection)
        if count > 0 and common.keys_exists(db_data[0], "Latency", "Avg"):
            data.append([head, db_data[0]['Latency']['Avg'] * 1000])
        else:
            data.append([head, "-"])
    return data


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
        if issue.type.name == "Defect" and issue.type.inward == "created by" and \
                issue.inwardIssue.key.startswith("TEST-"):
            tests.append(issue.inwardIssue.key)
    return tests


def get_detailed_reported_bugs(test_plan: str, username: str, password: str):
    """
    summary: Get detailed reported bugs from testplan.
    """
    test_executions = jira_api.get_test_executions_from_test_plan(test_plan, username, password)
    defects = defaultdict(list)
    for te_issue in test_executions:
        tests = jira_api.get_test_from_test_execution(te_issue["key"], username, password)
        for test in tests:
            if test["status"] == "FAIL" and test["defects"]:
                for defect in test["defects"]:
                    defects[defect["key"]].append(test["key"])
    data = [
        ["Detailed Reported Bugs"],
        ["Component", "Test ID", "Priority", "JIRA ID", "Status", "Description"],
    ]
    for defect, tests in defects.items():
        defect_details = jira_api.get_issue_details(defect, username, password)
        defect_details = defect_details.fields
        component = ""
        if defect_details.components:
            component = defect_details.components[0].name
        priority = defect_details.priority.name
        summary = defect_details.summary
        status = defect_details.status.name
        data.extend([[component, "/".join(tests), priority, defect, status, summary]])

    return data


def main():
    """Generate csv engineering report from test plan JIRA."""
    test_plans, uri, db_name, db_collection = common.get_args()
    rest, db_username, db_password = common.get_timings_db_details()
    username, password = jira_api.get_username_password()

    tps_info = [jira_api.get_details_from_test_plan(test_plan, username, password) if
                test_plan else "NA" for test_plan in test_plans]
    builds = [x["buildNo"] if x != 'NA' else 'NA' for x in tps_info]

    branch = tps_info[0]["branch"]

    data = []
    data.extend(jira_api.get_main_table_data(tps_info[0], "Engg"))
    data.extend([""])
    data.extend(jira_api.get_reported_bug_table_data(test_plans[0], username, password))
    data.extend([""])
    data.extend(jira_api.get_overall_qa_report_table_data(test_plans[0], test_plans[1],
                                                          builds[0], username,
                                                          password))
    data.extend([""])
    data.extend(get_component_issue_summary(test_plans, username, password))
    data.extend([""])
    data.extend(get_single_bucket_perf_stats(builds[0], branch, uri, db_name, db_collection))
    data.extend([""])
    data.extend(get_multiple_bucket_perf_stats(builds[0], branch, uri, db_name, db_collection))
    data.extend([""])
    data.extend(get_metadata_latencies(builds[0], uri, db_name, db_collection))
    data.extend([""])
    data.extend(common.get_timing_summary(test_plans, builds, rest, db_username, db_password))
    data.extend([""])
    data.extend(get_detailed_reported_bugs(test_plans[0], username, password))
    data.extend([""])
    with open(f"Engg_Report_{builds[0]}.csv", "w+", newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(data)


if __name__ == '__main__':
    main()
