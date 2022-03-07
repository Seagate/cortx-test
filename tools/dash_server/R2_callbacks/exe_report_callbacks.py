"""Executive Report Callbacks."""
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
# !/usr/bin/python
import json
from http import HTTPStatus

import dash_table
import numpy as np
import pandas as pd
import requests
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate

import common
from common import app


@app.callback(
    [Output('product_heading_exe', 'children'), Output('product_heading_eng', 'children'),
     Output('build_heading_exe', 'children'), Output('build_heading_eng', 'children'),
     Output('date_heading_exe', 'children'), Output('date_heading_eng', 'children')],
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_plan_dropdown', 'value'),
     State('test_team_dropdown', 'value')
     ]
)
def gen_tab_headers(n_clicks, branch, build_no, test_system, test_plan, test_team):
    """
    Generate Report headers with details.
    """
    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate
    product_heading = "Product : Lyve Rack 2"
    build_heading = "Build : " + str(build_no)
    date = "Date : "
    start_of_execution = "-"

    # Retrieve latest testplan for CortxQA for that specific build
    query = {"buildType": branch, "buildNo": build_no, "testPlanLabel": test_system, "latest": True}
    if test_team is None:
        query["testTeam"] = "CortxQA"
    else:
        query["testTeam"] = test_team

    if test_plan is None:
        tp = common.get_testplan_ID(query)
        if tp is not None:
            query["testPlanID"] = tp
    else:
        query["testPlanID"] = test_plan

    query_input = {
        "query": query,
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
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_plan_dropdown', 'value'),
     State('test_team_dropdown', 'value'),
     ]
)
def gen_table_reported_bugs(n_clicks, branch, build_no, test_system, test_plan, test_team):
    """
    Generate Priority wise and Cortx/Test issue table
    """
    issue_type = ["Blocker", "Critical", "Major", "Minor", "Trivial", "Total"]
    test_infra_issue_dict = {"Blocker": 0, "Critical": 0, "Major": 0, "Minor": 0,
                             "Trivial": 0, "Total": 0}
    cortx_issue_dict = {"Blocker": 0, "Critical": 0, "Major": 0, "Minor": 0,
                        "Trivial": 0, "Total": 0}

    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate

    query = {"buildType": branch, "buildNo": build_no, "testPlanLabel": test_system}

    if test_team is None:
        query["testTeam"] = "CortxQA"
    else:
        query["testTeam"] = test_team

    if test_plan is None:
        tp = common.get_testplan_ID(query)
        if tp is not None:
            query["testPlanID"] = tp
    else:
        query["testPlanID"] = test_plan

    query_input = {"query": query, "field": "issueIDs"}
    if common.DEBUG_PRINTS:
        print(f"(gen_table_reported_bugs) Query {query_input}")
    query_input.update(common.credentials)

    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query_input))
    if response.status_code == HTTPStatus.OK:
        issue_list = json.loads(response.text)["result"]
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

        for i_type in issue_type[:-1]:
            test_infra_issue_dict[i_type] = \
                df_test_infra_issue[df_test_infra_issue["issue_priority"] == i_type].shape[0]
            cortx_issue_dict[i_type] = \
                df_cortx_issue[df_cortx_issue["issue_priority"] == i_type].shape[0]
    else:
        print(f"(gen_table_reported_bugs)Error response : {response.status_code}")

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
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_plan_dropdown', 'value'),
     State('test_team_dropdown', 'value')]
)
def gen_table_overall_qa_report(n_clicks, branch, build_no, test_system, test_plan, test_team):
    """
    Generate Overall test reports along with the previous build reports
    """
    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate

    previous_build_list = common.r2_get_previous_builds(branch, build_no)
    overall_qa_data = {"Category": ["PASS", "FAIL", "ABORTED", "BLOCKED", "TOTAL"]}

    previous_build_list.insert(0, build_no)
    for build in previous_build_list:
        build_results = []
        # check latest testplan for that build
        query = {"buildType": branch, "buildNo": build, "testPlanLabel": test_system}
        if test_team is None:
            query["testTeam"] = "CortxQA"
        else:
            query["testTeam"] = test_team

        if test_plan is None or build != build_no:
            tp = common.get_testplan_ID(query)
            if tp is not None:
                query["testPlanID"] = tp
        else:
            query["testPlanID"] = test_plan

        # Query results per category
        for category in overall_qa_data["Category"]:
            if category == "TOTAL":
                try:
                    build_results.append(sum(build_results))
                except TypeError:
                    build_results.append("-")
            else:
                query["testResult"] = category
                query_input = {"query": query}
                if common.DEBUG_PRINTS:
                    print(f"(gen_table_overall_qa_report) Query : {query_input}")
                query_input.update(common.credentials)
                response = requests.request("GET", common.count_endpoint, headers=common.headers,
                                            data=json.dumps(query_input))

                if response.status_code == HTTPStatus.OK:
                    json_response = json.loads(response.text)
                    build_results.append(json_response["result"])
                elif response.status_code == HTTPStatus.NOT_FOUND:
                    # print(f"(gen_table_overall_qa_report) response {response.status_code}")
                    build_results.append(0)
                else:
                    print(f"(gen_table_overall_qa_report) response {response.status_code}")
                    build_results.append("-")
        overall_qa_data[build] = build_results

    df_overall_qa_report = pd.DataFrame(overall_qa_data)

    overall_qa_report = dash_table.DataTable(
        id="overall_qa_report",
        columns=[{"name": i, "id": i} for i in df_overall_qa_report.columns],
        data=df_overall_qa_report.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'row_index': 0}, 'color': '#229954'},
                                {'if': {'row_index': 1}, 'color': '#CB4335'},
                                {'if': {'row_index': 2}, 'color': '#2E4053'},
                                {'if': {'row_index': 3}, 'color': '#F39C12'},
                                {'if': {'row_index': 4}, 'color': '#a5a5b5'},
                                {'if': {'row_index': 5}, 'color': '#3498DB'},
                                ],
        style_cell=common.dict_style_cell
    )
    return overall_qa_report, overall_qa_report


@app.callback(
    Output('table_feature_breakdown_summary', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_plan_dropdown', 'value'),
     State('test_team_dropdown', 'value'),
     ]
)
def gen_table_feature_breakdown_summary(n_clicks, branch, build_no, test_system, test_plan,
                                        test_team):
    """
    Generate feature wise breakdown of test results.
    """
    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate

    query = {"buildType": branch, "buildNo": build_no, "testPlanLabel": test_system}
    if test_team is None:
        query["testTeam"] = "CortxQA"
    else:
        query["testTeam"] = test_team

    if test_plan is None:
        tp = common.get_testplan_ID(query)
        if tp is not None:
            query["testPlanID"] = tp
    else:
        query["testPlanID"] = test_plan

    query_input = {"query": query,
                   "projection": {"testResult": True, "feature": True}}
    if common.DEBUG_PRINTS:
        print("(gen_table_feature_breakdown_summary)Query :{}".format(query_input))
    query_input.update(common.credentials)

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
                        each["testResult"].lower() == "blocked":
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
        df_feature_breakdown_summary["% Failed"] = np.floor(
            df_feature_breakdown_summary["% Failed"])
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
        print(f"(gen_table_feature_breakdown_summary) response: {response.status_code}")
        feature_breakdown_summary = None
    return feature_breakdown_summary


@app.callback(
    Output('table_code_maturity', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_plan_dropdown', 'value'),
     State('test_team_dropdown', 'value'),
     ])
def gen_table_code_maturity(n_clicks, branch, build_no, test_system, test_plan, test_team):
    """
    Code Maturity with reference to the previous builds
    """
    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate

    previous_build_list = common.r2_get_previous_builds(branch, build_no, 3)
    data_code_maturity = {"Category": ["PASS", "FAIL", "ABORTED", "BLOCKED", "TOTAL"]}
    previous_build_list.reverse()
    previous_build_list.insert(0, build_no)

    for build in previous_build_list:
        build_results = []
        query = {"buildType": branch, "buildNo": build, "testPlanLabel": test_system}
        if test_team is None:
            query["testTeam"] = "CortxQA"
        else:
            query["testTeam"] = test_team

        if test_plan is None or build != build_no :
            tp = common.get_testplan_ID(query)
            if tp is not None:
                query["testPlanID"] = tp
        else:
            query["testPlanID"] = test_plan

        for category in data_code_maturity["Category"]:
            if category == "TOTAL":
                try:
                    build_results.append(sum(build_results))
                except TypeError:
                    build_results.append("-")
            else:

                query["testResult"] = category
                query_input = {"query": query}
                if common.DEBUG_PRINTS:
                    print(f"(gen_table_code_maturity) Query : {query_input}")
                query_input.update(common.credentials)
                response = requests.request("GET", common.count_endpoint, headers=common.headers,
                                            data=json.dumps(query_input))

                if response.status_code == HTTPStatus.OK:
                    json_response = json.loads(response.text)
                    build_results.append(json_response["result"])
                elif response.status_code == HTTPStatus.NOT_FOUND:
                    # print(f"(gen_table_code_maturity) response : {response.status_code}")
                    build_results.append(0)
                else:
                    print(f"(gen_table_code_maturity) response : {response.status_code}")
                    build_results.append("-")
        data_code_maturity[build] = build_results

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
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     ]
)
def gen_table_s3_bucket_perf(n_clicks, branch, build_no,test_system):
    """
    Single Bucket Performance Statistics using S3bench
    """
    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate

    return "No data available for R2"
