""" Engineers Report Callbacks."""
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
import pandas as pd
import requests
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
from pymongo.network import command

import common
from common import app


# Table : Reported Bugs : gen_table_reported_bugs --> Callback same as tab 1
# Table : Overall QA Report : gen_table_overall_qa_report --> Callback same as tab 1


@app.callback(
    Output('table_comp_summary', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_team_dropdown', 'value')]
)
def gen_table_comp_summary(n_clicks, branch, build_no, test_system, test_team):
    """
    Returns the component wise issues for current and previous builds.
    :param n_clicks: Input event
    :param branch: Build branch
    :param build_no: Build Number
    :param test_system: System type
    :param test_team: Testing team
    :return:
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    component_list = ["S3", "Provisioner", "CSM", "RAS", "Motr", "HA", "Hare"]
    # Query for previous build
    prev_build = common.r2_get_previous_builds(branch, build_no)
    if len(prev_build) == 1:
        build_no_list = [build_no, prev_build[0]]
    else:
        build_no_list = [build_no]
    # list of dictionary
    builds_details = {"Component": component_list}
    for build in build_no_list:
        query = {"buildType": branch, "buildNo": build}
        if test_system is not None:
            query["testPlanLabel"] = test_system
        if test_system is not None:
            query["testTeam"] = test_team
        query_input = {"query": query, "field": "issueIDs"}
        if common.DEBUG_PRINTS:
            print(f"(gen_table_comp_summary) Query {query_input}")
        query_input.update(common.credentials)
        response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            issue_list = json_response["result"]
            issue_df = common.get_issue_details(issue_list)
            temp_list = []
            for comp in component_list:
                temp_list.append(issue_df[issue_df.issue_comp == comp].shape[0])
            builds_details[build] = temp_list
        elif response.status_code == HTTPStatus.NOT_FOUND:
            print(f"(gen_table_comp_summary) Response code {response.status_code}")
            builds_details[build] = 0 * len(component_list)
        else:
            print(f"(gen_table_comp_summary) Response code {response.status_code}")
            builds_details[build] = '-' * len(component_list)
    df_comp_summary = pd.DataFrame(builds_details)
    comp_summary = dash_table.DataTable(
        id="comp_summary",
        columns=[{"name": i, "id": i} for i in df_comp_summary.columns],
        data=df_comp_summary.to_dict('records'),
        merge_duplicate_headers=True,
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'}
                                ],
        style_cell=common.dict_style_cell
    )
    return comp_summary


@app.callback(
    Output('table_timing_summary', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_team_dropdown', 'value')]
)
def gen_table_timing_summary(n_clicks, branch, build_no, test_system, test_team):
    """
    Returns the timing details for the build
    :param n_clicks: Input Event
    :return:
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    previous_build_list = common.r2_get_previous_builds(branch, build_no, 2)
    previous_build_list.reverse()
    build_seq = [build_no]
    build_seq.extend(previous_build_list)
    # timing parameters
    timing_parameters = {
        "nodeRebootTime": "Node Reboot",
        "allServicesStartTime": "Start All Services",
        "allServicesStopTime": "Stop All Services",
        "nodeFailoverTime": "Node Failover",
        "nodeFailbackTime": "Node Failback",
        "bucketCreationTime": "Bucket Creation",
        "bucketDeletionTime": "Bucket Deletion",
        "softwareUpdateTime": "Software Update",
        "firmwareUpdateTime": "Firmware Update",
        "startNodeTime": "Start Node",
        "stopNodeTime": "Stop Node"
    }
    data_timing_summary = {"Task": timing_parameters.values()}

    for build in build_seq:
        row = []
        for param in timing_parameters.keys():
            query = {"buildType": branch, "buildNo": build, param: {"$exists": True}}
            if test_system is not None:
                query["testPlanLabel"] = test_system
            if test_team is not None:
                query["testTeam"] = test_team

            query_input = {"query": query, "projection": {param: True}}
            query_input.update(common.credentials)
            if common.DEBUG_PRINTS:
                print("(gen_table_timing_summary)Query :{}".format(query_input))
            response = requests.request("GET", common.timing_endpoint, headers=common.headers,
                                        data=json.dumps(query_input))
            if response.status_code == HTTPStatus.OK:
                json_response = json.loads(response.text)
                parameter_data = json_response["result"]
                if parameter_data:
                    row.append(common.round_off(
                        sum(x[param] for x in parameter_data) / len(parameter_data)))
                else:
                    row.append("-")
            elif response.status_code == HTTPStatus.NOT_FOUND:
                # print(f"(gen_table_timing_summary) Response code {response.status_code}")
                row.append("-")
            else:
                print(f"(gen_table_timing_summary) Response code {response.status_code}")
                row.append("-")
        data_timing_summary[build] = row

    df_timing_summary = pd.DataFrame(data_timing_summary)
    timing_summary = dash_table.DataTable(
        id="timing_summary",
        columns=[{"name": i, "id": i} for i in df_timing_summary.columns],
        data=df_timing_summary.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Task"}, 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=common.dict_style_cell
    )
    return timing_summary


@app.callback(
    Output('table_detailed_s3_bucket_perf', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_team_dropdown', 'value')]
)
def gen_table_detailed_s3_bucket_perf(n_clicks, branch, build_no, test_system, test_team):
    """
    Single Bucket Performance Statistics (Average) using S3Bench (Detailed)
    :param n_clicks:
    :return:
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate
    if test_system is not None:
        # Add to query
        pass
    if test_team is not None:
        # Add to query
        pass

    return "No data available for R2"


@app.callback(
    Output('table_metadata_latency', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_team_dropdown', 'value')]
)
def gen_table_metadata_latency(n_clicks, branch, build_no, test_system, test_team):
    """
    Returns  table for Metadata Latency
    :param n_clicks:
    :return:
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate
    if test_system is not None:
        # Add to query
        pass
    if test_team is not None:
        # Add to query
        pass
    return "No data available for R2"


@app.callback(
    Output('table_multi_bucket_perf_stats', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_team_dropdown', 'value')]
)
def gen_table_multi_bucket_perf_stats(n_clicks, branch, build_no, test_system, test_team):
    """
    Multiple Buckets Performance Statistics(Average) using HSBench and COSBench
    :param n_clicks: Input Event
    :return:
    """

    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    if test_system is not None:
        # Add to query
        pass
    if test_team is not None:
        # Add to query
        pass
    return "No data available for R2"


@app.callback(
    Output('table_detail_reported_bugs', 'children'),
    [Input('submit_button', 'n_clicks'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_table_detail_reported_bugs(n_clicks, branch, build_no, test_system, test_team):
    """
    Table : List all the bugs for the specified inputs.
    :param n_clicks:Input Event
    :param branch:Build branch
    :param build_no:Build Number
    :param test_system:
    :param test_team:
    :return:
    """
    if n_clicks is None or branch is None or build_no is None or \
            test_system is None or test_team is None:
        raise PreventUpdate

    query_input = {
        "query": {"buildType": branch, "buildNo": build_no, "testPlanLabel": test_system,
                  "testTeam": test_team},
        "field": "issueIDs"}
    if common.DEBUG_PRINTS:
        print(f"(gen_table_detail_reported_bugs) Query:{query_input}")
    query_input.update(common.credentials)
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query_input))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        issue_list = json_response["result"]
        if common.DEBUG_PRINTS:
            print("Issue list (reported bugs)", issue_list)
        df_detail_reported_bugs = common.get_issue_details(issue_list)
        detail_reported_bugs = dash_table.DataTable(
            id="detail_reported_bugs",
            columns=[{"name": str(i).upper(), "id": i} for i in
                     df_detail_reported_bugs.columns],
            data=df_detail_reported_bugs.to_dict('records'),
            style_header=common.dict_style_header,
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'}
                                    ],
            style_cell=common.dict_style_cell
        )
    else:
        print(f"(gen_table_detail_reported_bugs) Response: {response.status_code}")
        detail_reported_bugs = None

    return detail_reported_bugs
