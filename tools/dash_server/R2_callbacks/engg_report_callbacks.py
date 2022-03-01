""" Engineers Report Callbacks."""
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
     State('test_plan_dropdown', 'value'),
     State('test_team_dropdown', 'value')]
)
def gen_table_comp_summary(n_clicks, branch, build_no, test_system,test_plan, test_team):
    """
    Returns the component wise issues for current and previous builds.
    :param n_clicks: Input event
    :param branch: Build branch
    :param build_no: Build Number
    :param test_system: System type
    :param test_team: Testing team
    :return:
    """
    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate

    component_list = ["Automation", "CSM", "CFT", "doc", "Foundation", "HA", "hare", "Monitor",
                      "Motr", "Provisioner", "S3Server", "UDX"]
    # Query for previous build
    prev_build = common.r2_get_previous_builds(branch, build_no)
    if len(prev_build) == 1:
        build_no_list = [build_no, prev_build[0]]
    else:
        build_no_list = [build_no]
    # list of dictionary
    builds_details = {"Component": component_list}
    for build in build_no_list:
        query = {"buildType": branch, "buildNo": build, "testPlanLabel":test_system}
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
     State('test_plan_dropdown', 'value'),
     State('test_team_dropdown', 'value')]
)
def gen_table_timing_summary(n_clicks, branch, build_no, test_system,test_plan, test_team):
    """
    Returns the timing details for the build
    :param n_clicks: Input Event
    :return:
    """
    if n_clicks is None or branch is None or build_no is None or test_system is None:
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
            query = {"buildType": branch, "buildNo": build,"testPlanLabel":test_system, param: {"$exists": True}}
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
                #print(f"(gen_table_timing_summary) Response code {response.status_code}")
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
    ]
)
def gen_table_detailed_s3_bucket_perf(n_clicks, branch, build_no, test_system):
    """
    Single Bucket Performance Statistics (Average) using S3Bench (Detailed)
    :param n_clicks:
    :return:
    """
    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate
    return "No data available for R2"


@app.callback(
    Output('table_metadata_latency', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
    ]
)
def gen_table_metadata_latency(n_clicks, branch, build_no, test_system):
    """
    Returns  table for Metadata Latency
    :param n_clicks:
    :return:
    """
    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate
    return "No data available for R2"


@app.callback(
    Output('table_multi_bucket_perf_stats', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     ]
)
def gen_table_multi_bucket_perf_stats(n_clicks, branch, build_no, test_system):
    """
    Multiple Buckets Performance Statistics(Average) using HSBench and COSBench
    :param n_clicks: Input Event
    :return:
    """

    if n_clicks is None or branch is None or build_no is None or test_system is None:
        raise PreventUpdate

    return "No data available for R2"


@app.callback(
    Output('table_detail_reported_bugs', 'children'),
    [Input('submit_button', 'n_clicks')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     State('test_system_dropdown', 'value'),
     State('test_plan_dropdown', 'value'),
     State('test_team_dropdown', 'value'),
     ]
)
def gen_table_detail_reported_bugs(n_clicks, branch, build_no, test_system,test_plan,test_team):
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
            test_system is None:
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

    query_input = {"query":query,"field": "issueIDs"}
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
        df_detail_reported_bugs["issue_no"] = df_detail_reported_bugs["issue_no"].\
            apply(common.add_link)

        col = []
        for i in df_detail_reported_bugs.columns:
            if i == "issue_no":
                col.append(
                    {"name": str(i).upper(), "id": i, "type": 'text', "presentation": "markdown"})
            else:
                col.append({"name": str(i).upper(), "id": i})

        detail_reported_bugs = dash_table.DataTable(
            id="detail_reported_bugs",
            columns=col,
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
