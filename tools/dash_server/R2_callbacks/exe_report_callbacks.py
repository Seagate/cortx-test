"""Executive Report Callbacks."""
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
# !/usr/bin/python
import json
from http import HTTPStatus

import dash_table
import numpy as np
import pandas as pd
import requests
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate

import common
from common import app


@app.callback(
    [Output('product_heading_exe', 'children'), Output('product_heading_eng', 'children'),
     Output('build_heading_exe', 'children'), Output('build_heading_eng', 'children'),
     Output('date_heading_exe', 'children'), Output('date_heading_eng', 'children')],
    [Input('submit_button', 'n_clicks'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_tab_headers(n_clicks, version, build_no, test_system, test_team):
    """
    Generate Report headers with details.
    """
    if n_clicks is None or version is None or build_no is None \
            or test_system is None or test_team is None:
        raise PreventUpdate

    product_heading = "Product : Lyve Rack 2"
    build_heading = "Build : " + str(build_no)
    date = "Date : "
    start_of_execution = "-"
    query_input = {
        "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                  "testTeam": test_team},
        "projection": {"testStartTime": True},
        "sort": {"testStartTime": 1}
    }
    query_input.update(common.credentials)
    response = requests.request("GET", common.search_endpoint, headers=common.headers,
                                data=json.dumps(query_input))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        if len(json_response["result"]) > 0:
            start_of_execution = json_response["result"][0]["testStartTime"]
    date = date + str(start_of_execution)
    return product_heading, product_heading, build_heading, build_heading, date, date


@app.callback(
    [Output('table_reported_bugs_engg', 'children'),
     Output('table_reported_bugs_exe', 'children')],
    [Input('submit_button', 'n_clicks'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_table_reported_bugs(n_clicks, version, build_no, test_system, test_team):
    """
    Generate Priority wise and Cortx/Test issue table
    """
    issue_type = ["Total", "Blocker", "Critical", "Major", "Minor", "Trivial"]
    test_infra_issue_dict = {"Total": 0, "Blocker": 0, "Critical": 0, "Major": 0, "Minor": 0,
                             "Trivial": 0}
    cortx_issue_dict = {"Total": 0, "Blocker": 0, "Critical": 0, "Major": 0, "Minor": 0,
                        "Trivial": 0}

    if n_clicks is None or version is None or build_no is None or \
            test_system is None or test_team is None:
        raise PreventUpdate

    query_input = {
        "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                  "testTeam": test_team},
        "field": "issueIDs"}

    query_input.update(common.credentials)
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query_input))
    if response.status_code == HTTPStatus.OK:
        issue_list =  json.loads(response.text)["result"]
        df_issue_details = common.get_issue_details(issue_list)
        # check issue type and priority
        # test issues
        df_test_infra_issue = df_issue_details.loc[
            df_issue_details["issue_comp"].isin(["CFT", "Automation"])]
        if common.DEBUG_PRINTS:
            print("test_infra issue {}".format(df_test_infra_issue))
        test_infra_issue_dict["Total"] = df_test_infra_issue.shape[0]

        # cortx issues
        df_cortx_issue = df_issue_details.loc[
            ~df_issue_details["issue_comp"].isin(["CFT", "Automation"])]
        if common.DEBUG_PRINTS:
            print("cortx issue {}".format(df_cortx_issue))
        df_cortx_issue["Total"] = df_cortx_issue.shape[0]

        for i_type in issue_type[1:]:
            test_infra_issue_dict[i_type] = \
                df_test_infra_issue[df_test_infra_issue["issue_priority"] == i_type].shape[0]
            cortx_issue_dict[i_type] = \
                df_cortx_issue[df_cortx_issue["issue_priority"] == i_type].shape[0]
    else:
        print("Error in gen table reported bugs : {}".format(response))

    df_reported_bugs = pd.DataFrame({"Priority": issue_type,
                                     "Test Infra Issues": test_infra_issue_dict.values(),
                                     "Cortx SW Issues": cortx_issue_dict.values()})
    reported_bugs = dash_table.DataTable(
        id="reported_bugs",
        columns=[{"name": i, "id": i} for i in df_reported_bugs.columns],
        data=df_reported_bugs.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'row_index': 0}, 'color': '#3498DB'},
                                {'if': {'row_index': 1}, 'color': '#CB4335'},
                                {'if': {'row_index': 2}, 'color': '#F39C12'},
                                {'if': {'row_index': 3}, 'color': '#2874A6'},
                                {'if': {'row_index': 4}, 'color': '#2E4053'},
                                {'if': {'row_index': 5}, 'color': '#229954'}
                                ],
        style_cell=common.dict_style_cell
    )
    return reported_bugs, reported_bugs


@app.callback(
    [Output('table_overall_qa_report_engg', 'children'),
     Output('table_overall_qa_report_exe', 'children')],
    [Input('submit_button', 'n_clicks'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_table_overall_qa_report(n_clicks, version, build_no, test_system, test_team):
    """
    Generate Overall test reports along with the previous build reports
    """
    if n_clicks is None or version is None or build_no is None or \
            test_system is None or test_team is None:
        raise PreventUpdate
    category = ["TOTAL", "PASS", "FAIL", "ABORTED", "BLOCKED", "TODO"]
    current_build = []
    previous_build = []

    # Get current build data
    query_input = {
        "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                  "testTeam": test_team},
        "projection": {"testResult": True}}
    query_input.update(common.credentials)
    response = requests.request("GET", common.search_endpoint, headers=common.headers,
                                data=json.dumps(query_input))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        for result_type in category[1:]:
            count = 0
            for each in json_response["result"]:
                if str(each["testResult"]).lower() == result_type.lower():
                    count = count + 1
            current_build.append(count)
        current_build.insert(0, sum(current_build))
        print("Current build overall_qa_report {}".format(current_build))
    else:
        print("Error current build received : {}".format(response))
        current_build = ["-", "-", "-", "-", "-", "-"]

    # Query and change build no to previous build
    query_input = {
        "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                  "testTeam": test_team},
        "projection": {"testResult": True}}
    query_input.update(common.credentials)
    print("Query :{}".format(query_input))
    response = requests.request("GET", common.search_endpoint, headers=common.headers,
                                data=json.dumps(query_input))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        for result_type in category[1:]:
            count = 0
            for each in json_response["result"]:
                if str(each["testResult"]).lower() == result_type.lower():
                    count = count + 1
            previous_build.append(count)
        previous_build.insert(0, sum(previous_build))
        print("previous build {}".format(previous_build))
    else:
        print("Error previous received : {}".format(response))
        previous_build = ["-", "-", "-", "-", "-", "-"]

    data_overall_qa_report = {"Category": category,
                              "Current Build": current_build,
                              "Previous Build": previous_build}
    df_overall_qa_report = pd.DataFrame(data_overall_qa_report)

    overall_qa_report = dash_table.DataTable(
        id="overall_qa_report",
        columns=[{"name": i, "id": i} for i in df_overall_qa_report.columns],
        data=df_overall_qa_report.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'row_index': 0}, 'color': '#3498DB'},
                                {'if': {'row_index': 1}, 'color': '#229954'},
                                {'if': {'row_index': 2}, 'color': '#CB4335'},
                                {'if': {'row_index': 3}, 'color': '#2E4053'},
                                {'if': {'row_index': 4}, 'color': '#F39C12'},
                                {'if': {'row_index': 5}, 'color': '#a5a5b5'}
                                ],
        style_cell=common.dict_style_cell
    )
    return overall_qa_report, overall_qa_report


@app.callback(
    Output('table_feature_breakdown_summary', 'children'),
    [Input('submit_button', 'n_clicks'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_table_feature_breakdown_summary(n_clicks, version, build_no, test_system, test_team):
    """
    Generate feature wise breakdown of test results.
    """
    if n_clicks is None or version is None or build_no is None or \
            test_system is None or test_team is None:
        raise PreventUpdate

    query_input = {
        "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                  "testTeam": test_team},
        "projection": {"testResult": True, "feature": True}}
    query_input.update(common.credentials)
    print("Query :{}".format(query_input))
    response = requests.request("GET", common.search_endpoint, headers=common.headers,
                                data=json.dumps(query_input))
    if response.status_code == HTTPStatus.OK:
        # retrieve feature list dynamically
        feature_list = []
        json_response = json.loads(response.text)
        for each in json_response["result"]:
            feature_list.append(each["feature"])
        feature_list = list(set(feature_list))
        pass_count_list = []
        fail_count_list = []
        total_count_list = []
        for feature in feature_list:
            pass_count = 0
            fail_count = 0
            for each in json_response["result"]:
                if each["feature"] == feature and each["testResult"].lower() == "pass":
                    pass_count = pass_count + 1
                elif each["feature"] == feature and each["testResult"].lower() == "fail" or \
                        each[
                            "testResult"].lower() == "blocked":
                    fail_count = fail_count + 1
                else:
                    pass
            pass_count_list.append(pass_count)
            fail_count_list.append(fail_count)
            total_count_list.append(pass_count + fail_count)

        # add total as last row of table
        feature_list.append("Total")
        pass_count_list.append(sum(pass_count_list))
        fail_count_list.append(sum(fail_count_list))
        total_count_list.append(sum(total_count_list))

        if common.DEBUG_PRINTS:
            print("Feature_list {}".format(feature_list))
            print("Pass list {}".format(pass_count_list))
            print("Fail list {}".format(fail_count_list))
            print("Total list {}".format(total_count_list))

        data_feature_breakdown_summary = {"Feature": feature_list,
                                          "Total": total_count_list,
                                          "Passed": pass_count_list,
                                          "Failed": fail_count_list,
                                          }
        df_feature_breakdown_summary = pd.DataFrame(data_feature_breakdown_summary)
        df_feature_breakdown_summary["% Passed"] = (
                df_feature_breakdown_summary["Passed"] /
                df_feature_breakdown_summary["Total"] * 100)
        df_feature_breakdown_summary["% Passed"] = np.ceil(df_feature_breakdown_summary["% Passed"])
        df_feature_breakdown_summary["% Failed"] = (df_feature_breakdown_summary["Failed"] /
                                                    df_feature_breakdown_summary[
                                                        "Total"] * 100)
        df_feature_breakdown_summary["% Failed"] = np.floor(df_feature_breakdown_summary["% Failed"])
        feature_breakdown_summary = dash_table.DataTable(
            id="feature_breakdown_summary",
            columns=[{"name": i, "id": i} for i in df_feature_breakdown_summary.columns],
            data=df_feature_breakdown_summary.to_dict('records'),
            style_header=common.dict_style_header,
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                    {'if': {'row_index': len(total_count_list)},
                                     'backgroundColor': "#c1c1d6"},
                                    {'if': {'column_id': "Feature"},
                                     'backgroundColor': "#b9b9bd"}
                                    ],
            style_cell=common.dict_style_cell
        )
    else:
        feature_breakdown_summary = None
    return feature_breakdown_summary


@app.callback(
    Output('table_code_maturity', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_code_maturity(n_clicks):
    """
    Code Maturity with reference to the previous builds
    """
    if n_clicks is None:
        raise PreventUpdate
    data_code_maturity = {"Category": ["Total", "Pass", "Fail", "Aborted", "Blocked"],
                          "Current Build": ["1", "2", "3", "4", "5"],
                          "Prev Build": ["1", "2", "3", "4", "5"],
                          "Prev Build 1": ["1", "2", "3", "4", "5"],
                          "Prev Build 2": ["1", "2", "3", "4", "5"],
                          }
    df_code_maturity = pd.DataFrame(data_code_maturity)
    code_maturity = dash_table.DataTable(
        id="code_maturity",
        columns=[{"name": i, "id": i} for i in df_code_maturity.columns],
        data=df_code_maturity.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Category"}, 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=common.dict_style_cell
    )
    return code_maturity


@app.callback(
    Output('table_s3_bucket_perf', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_s3_bucket_perf(n_clicks):
    """
    Single Bucket Performance Statistics using S3bench
    """
    if n_clicks is None:
        raise PreventUpdate
    data_s3_bucket_perf = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)"],
        "4KB Object": ["1", "2", "3", "4"],
        "256MB Object": ["1", "2", "3", "4"],
    }
    df_s3_bucket_perf = pd.DataFrame(data_s3_bucket_perf)
    s3_bucket_perf = dash_table.DataTable(
        id="code_maturity",
        columns=[{"name": i, "id": i} for i in df_s3_bucket_perf.columns],
        data=df_s3_bucket_perf.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Statistics"},
                                 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=common.dict_style_cell
    )
    return s3_bucket_perf
