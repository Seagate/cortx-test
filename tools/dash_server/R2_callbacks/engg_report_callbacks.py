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

import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_table
import pandas as pd
import requests
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import common
from common import app


# Table : Reported Bugs : gen_table_reported_bugs --> Callback same as tab 1
# Table : Overall QA Report : gen_table_overall_qa_report --> Callback same as tab 1


@app.callback(
    Output('table_comp_summary', 'children'),
    [Input('submit_button', 'n_clicks'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
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
    if n_clicks is None or branch is None or build_no is None or \
            test_system is None or test_team is None:
        raise PreventUpdate

    component_list = ["S3", "Provisioner", "CSM", "RAS", "Motr", "HA"]
    # **Query for previous build
    # current build, previous build
    build_no_list = [build_no, build_no]
    # list of dictionary
    builds_details = []

    for build in build_no_list:
        query_input = {
            "query": {"buildType": branch, "buildNo": build, "testPlanLabel": test_system,
                      "testTeam": test_team},
            "field": "issueIDs"}

        query_input.update(common.credentials)
        response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            issue_list = json_response["result"]
            issue_df = common.get_issue_details(issue_list)
            build_dict = {}
            for comp in component_list:
                build_dict[comp] = issue_df[issue_df.issue_comp == comp].shape[0]
            builds_details.append(build_dict)

    df_comp_summary = pd.DataFrame({
        "Component": component_list,
        "Current Build": builds_details[0].values(),
        "Previous Build ": builds_details[1].values()
    })
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
    [Input('submit_button', 'n_clicks')]
)
def gen_table_timing_summary(n_clicks):
    """
    Returns the timing details for the build
    :param n_clicks: Input Event
    :return:
    """
    if n_clicks is None:
        raise PreventUpdate
    data_timing_summary = {
        "Task": ["Update", "Deployment", "Boxing", "Unboxing", "Onboarding", "Firmware Update",
                 "Bucket Creation",
                 "Bucket Deletion"],
        "Current Build": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "Prev Build": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "Prev Build 1": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "Prev Build 2": ["1", "2", "3", "4", "5", "6", "7", "8"],
    }
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
    [Input('submit_button', 'n_clicks')]
)
def gen_table_detailed_s3_bucket_perf(n_clicks):
    """
    Single Bucket Performance Statistics (Average) using S3Bench (Detailed)
    :param n_clicks:
    :return:
    """
    if n_clicks is None:
        raise PreventUpdate
    data_detailed_s3_bucket_perf = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS", "Write TTFB(ms)", "Read TTFB(ms)"],
        "4KB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "100KB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "1MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "5MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "36MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "64MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "128MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "256MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
    }
    df_detailed_s3_bucket_perf = pd.DataFrame(data_detailed_s3_bucket_perf)
    detailed_s3_bucket_perf = dash_table.DataTable(
        id="detailed_s3_bucket_perf",
        columns=[{"name": i, "id": i} for i in df_detailed_s3_bucket_perf.columns],
        data=df_detailed_s3_bucket_perf.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Statistics"}, 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=common.dict_style_cell
    )
    return detailed_s3_bucket_perf


@app.callback(
    Output('table_metadata_latency', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_metadata_latency(n_clicks):
    """
    Returns  table for Metadata Latency
    :param n_clicks:
    :return:
    """
    if n_clicks is None:
        raise PreventUpdate
    data_metadata_latency = {
        "Operation Latency": ["Add/Edit Object Tags", "Read Object Tags", "Read Object Metadata"],
        "Response Time(ms)": ["1", "2", "3"],
    }
    df_metadata_latency = pd.DataFrame(data_metadata_latency)
    metadata_latency = dash_table.DataTable(
        id="metadata_latency",
        columns=[{"name": i, "id": i} for i in df_metadata_latency.columns],
        data=df_metadata_latency.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Operation Latency"},
                                 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=common.dict_style_cell
    )
    return metadata_latency




@app.callback(
    Output('table_multi_bucket_perf_stats', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_multi_bucket_perf_stats(n_clicks):
    """
    Multiple Buckets Performance Statistics(Average) using HSBench and COSBench
    :param n_clicks: Input Event
    :return:
    """

    if n_clicks is None:
        raise PreventUpdate

    final_rows = []

    # HS bench 1 bucket 1000 Objects 100 Sessions
    data = {"Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                           "Read Latency(ms)",
                           "Write IOPS", "Read IOPS"],
            "4KB": ["1", "2", "3", "4", "5", "6"],
            "100KB": ["1", "2", "3", "4", "5", "6"],
            "1MB": ["1", "2", "3", "4", "5", "6"],
            "5MB": ["1", "2", "3", "4", "5", "6"],
            "36MB": ["1", "2", "3", "4", "5", "6"],
            "64MB": ["1", "2", "3", "4", "5", "6"],
            "128MB": ["1", "2", "3", "4", "5", "6"],
            "256MB": ["1", "2", "3", "4", "5", "6"],
            }
    temp_df = pd.DataFrame(data)
    text = ["Hsbench", html.Br(), "1 Buckets", html.Br(), "100 Objects", html.Br(), "100 Sessions"]
    final_rows.extend(common.get_data_to_html_rows(temp_df, text, 6))

    # HS bench 10 bucket 100 Objects 100 Sessions
    data = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    temp_df = pd.DataFrame(data)
    text = ["Hsbench", html.Br(), "10 Buckets", html.Br(), "100 Objects", html.Br(), "100 Sessions"]
    final_rows.extend(common.get_data_to_html_rows(temp_df, text, 6))

    # HS bench 50 bucket 100 Objects 100 Sessions
    data = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    temp_df = pd.DataFrame(data)
    text = ["Hsbench", html.Br(), "50 Buckets", html.Br(), "100 Objects", html.Br(), "100 Sessions"]
    final_rows.extend(common.get_data_to_html_rows(temp_df, text, 6))

    # Cosbench 1 bucket 100 Objects 100 Sessions
    data = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    temp_df = pd.DataFrame(data)
    text = ["Cosbench", html.Br(), "1 Buckets", html.Br(), "100 Objects", html.Br(), "100 Sessions"]
    final_rows.extend(common.get_data_to_html_rows(temp_df, text, 6))

    # Cosbench 10 bucket 100 Objects 100 Sessions
    data = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    temp_df = pd.DataFrame(data)
    text = ["Cosbench", html.Br(), "10 Buckets", html.Br(), "100 Objects", html.Br(),
            "100 Sessions"]
    final_rows.extend(common.get_data_to_html_rows(temp_df, text, 6))

    # Cosbench 50 bucket 100 Objects 100 Sessions
    data = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    temp_df = pd.DataFrame(data)
    text = ["Cosbench", html.Br(), "50 Buckets", html.Br(), "100 Objects", html.Br(),
            "100 Sessions"]
    final_rows.extend(common.get_data_to_html_rows(temp_df, text, 6))

    columns = ["Bench"]
    columns.extend(temp_df.columns)
    table_headers = [html.Thead(html.Tr([html.Th(col) for col in columns]))]
    table_body = [html.Tbody(final_rows)]
    table = dbc.Table(table_headers + table_body, bordered=True,
                      className="caption-Top col-xs-6",
                      hover=True,
                      responsive=True,
                      striped=True,
                      style=common.dict_style_cell)
    return table


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

    query_input.update(common.credentials)
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query_input))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        issue_list = json_response["result"]
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
        detail_reported_bugs = None

    return detail_reported_bugs
