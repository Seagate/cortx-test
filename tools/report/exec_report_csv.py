"""Script used to generate executive csv report."""
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
# -*- coding: utf-8 -*-
import csv
from collections import Counter

import numpy as np
import pandas as pd
from jira import JIRA

import common
import jira_api
import mongodb_api


def get_feature_breakdown_summary_table_data(test_plan: str, username: str, password: str):
    """Get feature breakdown summary table data."""
    df_feature_data = pd.DataFrame(columns=["Pass", "Fail", "Total"])
    jira_url = 'https://jts.seagate.com/'
    options = {'server': jira_url}
    jira = JIRA(options, basic_auth=(username, password))
    for feature in jira_api.FEATURES:
        df_feature_data.loc[feature.lstrip()] = [
            jira.search_issues(
                f'issue in testPlanTests("{test_plan}", "PASS") AND "Test Domain" = "{feature}"',
                maxResults=500, json_result=True)["total"],
            jira.search_issues(
                f'issue in testPlanTests("{test_plan}", "FAIL") AND "Test Domain" = "{feature}"',
                maxResults=500, json_result=True)["total"],
            jira.search_issues(
                f'issue in testPlanTests("{test_plan}") AND "Test Domain" = "{feature}"',
                maxResults=500, json_result=True)["total"]
        ]
    # Drop features with 0 data in all columns
    df_feature_data = df_feature_data[(df_feature_data > 0)].dropna(how="all")

    # Add % pass and % fail columns
    df_feature_data["% Pass"] = (
                df_feature_data["Pass"].divide(df_feature_data["Total"]) * 100).fillna(0).apply(
        np.ceil)
    df_feature_data["% Fail"] = (
                df_feature_data["Fail"].divide(df_feature_data["Total"]) * 100).fillna(0).apply(
        np.floor)

    df_feature_data.loc["Total"] = [df_feature_data.iloc[:, 0].sum(),
                                    df_feature_data.iloc[:, 1].sum(),
                                    df_feature_data.iloc[:, 2].sum(), "-", "-"]
    df_feature_data.fillna(0, inplace=True)
    feature_data = df_feature_data.reset_index().values.tolist()
    feature_data.insert(0, ["Feature", "Pass", "Fail", "Total", "% Pass", "% Fail"])
    feature_data.insert(0, ["Feature Breakdown Summary"])
    return feature_data


def get_code_maturity_data(test_plan: str, test_plan1: str, test_plan2: str,
                           username: str, password: str):
    """Get code maturity data."""
    counters = []
    builds = []
    for t_plan in [test_plan, test_plan1, test_plan2]:
        if t_plan:
            tests = jira_api.get_test_list_from_test_plan(t_plan, username, password)
            counters.append(Counter(test['latestStatus'] for test in tests))
            builds.append(
                jira_api.get_details_from_test_plan(t_plan, username, password)["buildNo"])
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


def get_single_bucket_perf_data(build, uri, db_name, db_collection):
    """Get Single Bucket performance data for executive report"""
    data = [["Single Bucket Performance Statistics (Average) using S3Bench - in a Nutshell"],
            ["Statistics", "4 KB Object", "256 MB Object"]]
    operations = ["Write", "Read"]
    stats = ["Throughput", "Latency"]
    objects_sizes = ["4Kb", "256Mb"]
    for operation in operations:
        for stat in stats:
            if stat == "Latency":
                temp_data = [f"{operation} {stat} (MBps)"]
            else:
                temp_data = [f"{operation} {stat} (ms)"]
            for objects_size in objects_sizes:
                query = {'Build': build, 'Name': 'S3bench', 'Object_Size': objects_size,
                         'Operation': operation}
                count = mongodb_api.count_documents(query=query, uri=uri, db_name=db_name,
                                                    collection=db_collection)
                db_data = mongodb_api.find_documents(query=query, uri=uri, db_name=db_name,
                                                     collection=db_collection)
                if stat == "Latency":
                    if count > 0 and common.keys_exists(db_data[0], stat, "Avg"):
                        temp_data.append(common.round_off(db_data[0][stat]["Avg"] * 1000))
                    else:
                        temp_data.append("-")
                elif stat == "Throughput":
                    if count > 0 and common.keys_exists(db_data[0], stat):
                        temp_data.append(common.round_off(db_data[0][stat]))
                    else:
                        temp_data.append("-")
                else:
                    temp_data.append("-")
            data.extend([temp_data])
    return data


def main():
    """Generate csv executive report from test plan JIRA."""
    test_plans, uri, db_name, db_collection = common.get_args()
    rest, db_username, db_password = common.get_timings_db_details()
    username, password = jira_api.get_username_password()

    tps_info = [jira_api.get_details_from_test_plan(test_plan, username, password) if
                test_plan else "NA" for test_plan in test_plans]
    builds = [x["buildNo"] if x != 'NA' else 'NA' for x in tps_info]

    data = []
    data.extend(jira_api.get_main_table_data(tps_info[0], "Exec"))
    data.extend([""])
    data.extend(jira_api.get_reported_bug_table_data(test_plans[0], username, password))
    data.extend([""])
    data.extend(jira_api.get_overall_qa_report_table_data(test_plans[0], test_plans[1],
                                                          builds[0], username, password))
    data.extend([""])
    data.extend(get_feature_breakdown_summary_table_data(
        test_plans[0], username, password))
    data.extend([""])
    data.extend(get_code_maturity_data(test_plans[0], test_plans[1], test_plans[2],
                                       username, password))
    data.extend([""])
    data.extend(get_single_bucket_perf_data(builds[0], uri, db_name, db_collection))
    data.extend([""])
    data.extend(common.get_timing_summary(test_plans, builds, rest, db_username, db_password))
    data.extend([""])
    with open(f"Exec_Report_{builds[0]}.csv", "w+", newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(data)


if __name__ == '__main__':
    main()
