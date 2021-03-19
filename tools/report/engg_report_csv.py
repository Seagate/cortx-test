# -*- coding: utf-8 -*-
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

import argparse
import csv
from collections import defaultdict

import common
import jira_api
import mongodb_api

OPERATIONS = ["write", "read"]
STATS = ["Throughput", "Latency", "IOPS"]
COSBENCH_CONFIG = [[1, 1000, 100], [10, 100, 100], [50, 100, 100]]
CB_OBJECTS_SIZES = ["4 KB", "100 KB", "1 MB", "5 MB", "36 MB", "64 MB", "128 MB", "256 MB"]
HSBENCH_CONFIG = [[1, 1000, 100], [10, 1000, 100], [50, 5000, 100]]
HB_OBJECTS_SIZES = ["4Kb", "100Kb", "1Mb", "5Mb", "36Mb", "64Mb", "128Mb", "256Mb"]


def get_component_breakup_from_testplan(test_plan: str, username: str, password: str):
    """Get component breakup from testplan."""
    te_keys = jira_api.get_test_executions_from_test_plan(test_plan, username, password)
    te_keys = [te_key["key"] for te_key in te_keys]
    components = {}
    for test_execution in te_keys:
        tests = jira_api.get_test_from_test_execution(test_execution, username, password)
        fail_count = sum(d['status'] == 'FAIL' for d in tests)
        pass_count = sum(d['status'] == 'PASS' for d in tests)
        total_count = len(tests)
        detail = jira_api.get_issue_details(test_execution, username, password)
        component = detail.fields.labels[0]
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
            builds.append(jira_api.get_build_from_test_plan(t_plan, username, password))
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


def get_single_bucket_perf_stats(build, uri, db_name, db_collection):
    """Get single bucket performance data for engineering report"""
    data = [["Single Bucket Performance Statistics (Average) using S3Bench"],
            ["Statistics", "4 KB", "100 KB", "1 MB", "5 MB", "36 MB", "64 MB", "128 MB",
             "256 MB"]]
    operations = ["Write", "Read"]
    stats = ["Throughput", "Latency", "IOPS", "TTFB"]
    objects_sizes = ["4Kb", "100Kb", "1Mb", "5Mb", "36Mb", "64Mb", "128Mb", "256Mb"]
    for operation in operations:
        for stat in stats:
            if stat in ["Latency", "TTFB"]:
                temp_data = [f"{operation} {stat} (ms)"]
            elif stat in ["Throughput"]:
                temp_data = [f"{operation} {stat} (MBps)"]
            else:
                temp_data = [f"{operation} {stat}"]
            for obj_size in objects_sizes:
                query = {'Build': build, 'Operation': operation, 'Object_Size': obj_size}
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
                    if count > 0 and common.keys_exists(db_data[0], stat):
                        temp_data.append(common.round_off(db_data[0][stat]))
                    else:
                        temp_data.append("-")
            data.extend([temp_data])
    return data


def get_cosbench_data(build, uri, db_name, db_collection):
    """Read Cosbench data from DB"""
    data = []
    for configs in COSBENCH_CONFIG:
        row_num = 0
        for operation in OPERATIONS:
            for stat in STATS:
                row_num += 1
                head = ""
                if row_num == 2:
                    head = "Cosbench"
                elif row_num == 3:
                    head = f"{configs[0]} Buckets"
                elif row_num == 4:
                    head = f"{configs[1]} Objects"
                elif row_num == 5:
                    head = f"{configs[2]} Sessions"
                temp_data = [head, f"{operation.capitalize()} {stat}"]
                for obj_size in CB_OBJECTS_SIZES:
                    query = {'Build': build, 'Name': "Cosbench", 'Operation': operation,
                             'Object_Size': obj_size, 'Buckets': configs[0], 'Objects': configs[1],
                             'Sessions': configs[2]}
                    count = mongodb_api.count_documents(query=query, uri=uri, db_name=db_name,
                                                        collection=db_collection)
                    db_data = mongodb_api.find_documents(query=query, uri=uri, db_name=db_name,
                                                         collection=db_collection)

                    if count > 0 and stat == "Latency" \
                            and common.keys_exists(db_data[0], stat, "Avg"):
                        temp_data.append(common.round_off(db_data[0][stat]["Avg"]))
                    elif count > 0 and common.keys_exists(db_data[0], stat):
                        temp_data.append(common.round_off(db_data[0][stat]))
                    else:
                        temp_data.append("-")
                data.append(temp_data)
    return data


def get_hsbench_data(build, uri, db_name, db_collection):
    """Read Hsbench data from DB"""
    data = []
    for configs in HSBENCH_CONFIG:
        row_num = 0
        for operation in OPERATIONS:
            for stat in STATS:
                row_num += 1
                head = ""
                if row_num == 2:
                    head = "Hsbench"
                elif row_num == 3:
                    head = f"{configs[0]} Buckets"
                elif row_num == 4:
                    head = f"{int(configs[1] / configs[0])} Objects"
                elif row_num == 5:
                    head = f"{configs[2]} Sessions"
                temp_data = [head, f"{operation.capitalize()} {stat}"]
                for obj_size in HB_OBJECTS_SIZES:
                    query = {'Build': build, 'Name': "Hsbench", 'Operation': operation,
                             'Object_Size': obj_size, 'Buckets': configs[0], 'Objects': configs[1],
                             'Sessions': configs[2]}
                    count = mongodb_api.count_documents(query=query, uri=uri, db_name=db_name,
                                                        collection=db_collection)
                    db_data = mongodb_api.find_documents(query=query, uri=uri, db_name=db_name,
                                                         collection=db_collection)

                    if count > 0 and common.keys_exists(db_data[0], stat):
                        temp_data.append(common.round_off(db_data[0][stat]))
                    else:
                        temp_data.append("-")
                data.append(temp_data)
    return data


def get_multiple_bucket_perf_stats(build, uri, db_name, db_collection):
    """Get multiple bucket performance data"""
    data = [["Multiple Buckets Performance Statistics (Average) using HSBench and COSBench"],
            ["Bench", "Statistics", "4 KB", "100 KB", "1 MB", "5 MB", "36 MB", "64 MB", "128 MB",
             "256 MB"]]

    data.extend(get_cosbench_data(build, uri, db_name, db_collection))
    data.extend(get_hsbench_data(build, uri, db_name, db_collection))
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


def get_args():
    """Parse arguments and collect database information"""
    parser = argparse.ArgumentParser()
    parser.add_argument('tp', help='Testplan for current build')
    parser.add_argument('--tp1', help='Testplan for current-1 build', default=None)
    parser.add_argument('--tp2', help='Testplan for current-2 build', default=None)
    parser.add_argument('--tp3', help='Testplan for current-3 build', default=None)

    test_plans = parser.parse_args()

    uri, db_name, db_collection = common.get_perf_db_details()
    return test_plans, uri, db_name, db_collection


def main():
    """Generate csv engineering report from test plan JIRA."""
    test_plans, uri, db_name, db_collection = get_args()
    rest, db_username, db_password = common.get_timings_db_details()
    username, password = jira_api.get_username_password()

    tp_ids = [test_plans.tp, test_plans.tp1, test_plans.tp2, test_plans.tp3]
    builds = [jira_api.get_build_from_test_plan(test_plan, username, password) if
              test_plan else "NA" for test_plan in tp_ids]

    data = []
    data.extend(jira_api.get_main_table_data(test_plans.tp))
    data.extend([""])
    data.extend(jira_api.get_reported_bug_table_data(test_plans.tp, username, password))
    data.extend([""])
    data.extend(jira_api.get_overall_qa_report_table_data(test_plans.tp, test_plans.tp1,
                                                          builds[0], username,
                                                          password))
    data.extend([""])
    data.extend(get_component_level_summary(tp_ids, username, password))
    data.extend([""])
    data.extend(get_single_bucket_perf_stats(builds[0], uri, db_name, db_collection))
    data.extend([""])
    data.extend(get_multiple_bucket_perf_stats(builds[0], uri, db_name, db_collection))
    data.extend([""])
    data.extend(get_metadata_latencies(builds[0], uri, db_name, db_collection))
    data.extend([""])
    data.extend(common.get_timing_summary(tp_ids, builds, rest, db_username, db_password))
    data.extend([""])
    data.extend(get_detailed_reported_bugs(test_plans.tp, username, password))
    data.extend([""])
    with open("../engg_report.csv", "a", newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(data)


if __name__ == '__main__':
    main()
