"""LDR 1 Engineering Report Callbacks."""
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, branch 2.0 (the "License");
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

import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_table
import pandas as pd
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate

import R1_callbacks.r1_perf_tables as r1_perf_tables
import common
import mongodbAPIs as r1Api
import perfdbAPIs as perf_api
import timingAPIs as timingAPIs
from common import app


@app.callback(
    Output('r1_table_comp_summary', 'children'),
    [Input('submit_button', 'n_clicks')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')]
)
def gen_table_comp_summary(n_clicks, branch, build_no, ):
    """
    Returns the component wise results for current and previous builds.
    :param n_clicks: Input event
    :param branch: Build branch
    :param build_no: Build Number
    :return:
    """

    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    component_list = ["S3", "Provisioner", "CSM", "RAS", "Motr", "HA", "Locust", "Cosbench",
                      "Data Recovery", "Node Recovery", "Total"]
    cursor = r1Api.find({'info': 'build sequence R1'})
    build_list = cursor[0][branch]
    if build_list.index(build_no) > 1:
        prev_build_no = build_list[build_list.index(build_no) - 1]
    else:
        prev_build_no = []
    build_no_list = [build_no]
    build_no_list.extend(prev_build_no)
    # list of dictionary
    data = {"Component": component_list}
    columns_data = [{"name": ["Component", ""], "id": "Component"}]
    for build in build_no_list:
        pass_dict = {}
        fail_dict = {}
        for comp in component_list:
            if comp == "Total":
                continue
            pass_dict[comp] = r1Api.count_documents(
                {'build': build, 'deleted': False, 'testResult': 'PASS',
                 'testExecutionLabels': comp})
            fail_dict[comp] = r1Api.count_documents(
                {'build': build, 'deleted': False, 'testResult': 'FAIL',
                 'testExecutionLabels': comp})
        pass_dict["Total"] = sum(pass_dict.values())
        fail_dict["Total"] = sum(fail_dict.values())
        tmp_str_pass = build + "_pass"
        tmp_str_fail = build + "_fail"
        data[tmp_str_pass] = pass_dict.values()
        data[tmp_str_fail] = fail_dict.values()
        columns_data.append({"name": [build, "Pass"], "id": tmp_str_pass})
        columns_data.append({"name": [build, "Fail"], "id": tmp_str_fail})

    df_comp_summary = pd.DataFrame(data)
    comp_summary = dash_table.DataTable(
        id="comp_summary",
        columns=columns_data,
        data=df_comp_summary.to_dict('records'),
        merge_duplicate_headers=True,
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'}
                                ],
        style_cell=common.dict_style_cell
    )
    return comp_summary


@app.callback(
    Output('r1_table_detail_reported_bugs', 'children'),
    [Input('submit_button', 'n_clicks')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')]
)
def gen_table_detail_reported_bugs(n_clicks, branch, build_no):
    """
    Table : List all the bugs for the specified inputs.
    :param n_clicks:Input Event
    :param branch:Build branch
    :param build_no:Build Number

    :return:
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    issue_list = r1Api.find_distinct("defectID", {"build": build_no, 'deleted': False})
    print("Issue list (reported bugs)", issue_list)
    df_detail_reported_bugs = common.get_issue_details(issue_list)
    df_detail_reported_bugs["issue_no"] = df_detail_reported_bugs["issue_no"]. \
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

    return detail_reported_bugs


@app.callback(
    Output('r1_table_timing_summary', 'children'),
    [Input('submit_button', 'n_clicks')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')]
)
def gen_table_timing_summary(n_clicks, branch, build_no):
    """
    Returns the timing details for the build
    :param n_clicks: Input Event
    :return:
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate
    timing_list = ['updateTime', 'deploymentTime', 'boxingTime', 'unboxingTime', 'onboardingTime',
                   'firmwareUpdateTime', 'nodeRebootTime', 'nodeStarTime', 'nodeStopTime',
                   'nodeFailoverTime', 'nodeFailbackTime', 'allServiceStopTime',
                   'allServiceStartTime', 'bucketCreationTime', 'bucketDeletionTime']

    cursor = r1Api.find({'info': 'build sequence R1'})
    build_list = cursor[0][branch]
    if build_list.index(build_no) > 1:
        prev_build_no = build_list[build_list.index(build_no) - 1]
        build_no_list = [build_no, prev_build_no]
    else:
        prev_build_no = []
        build_no_list = [build_no]
    timing_data = []
    for build in build_no_list:
        data_list = []
        for timing in timing_list:
            cursor = timingAPIs.find_distinct(timing, {'build': build})
            try:
                data = sum(cursor) / len(cursor)
            except Exception as ex:
                # print("Exception received while calculating average{}".format(ex))
                data = "-"
            data_list.append(data)
        timing_data.append(data_list)

    data_timing_summary = {
        "Task": timing_list,
        build_no: timing_data[0]
    }
    if prev_build_no:
        data_timing_summary[prev_build_no] = timing_data[1]

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
    Output('r1_table_detailed_s3_bucket_perf', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')]
)
def gen_table_detailed_s3_bucket_perf(n_clicks, branch, build_no):
    """
    Single Bucket Performance Statistics (Average) using S3Bench
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    df_det_s3_bucket_perf = r1_perf_tables.get_detailed_s3_bucket_perf(build_no)
    det_s3_bucket_perf = dash_table.DataTable(
        id="Detailed S3 Bucket Perf",
        columns=[{"name": i, "id": i} for i in df_det_s3_bucket_perf.columns],
        data=df_det_s3_bucket_perf.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Statistics"},
                                 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=common.dict_style_cell
    )
    return det_s3_bucket_perf


@app.callback(
    Output('r1_table_metadata_latency', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')]
)
def gen_table_metadata_latency(n_clicks, branch, build_no):
    """
    Metadata Latencies(captured with 1KB object)
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    df_metadata_latency = r1_perf_tables.get_metadata_latencies(build_no)
    metadata_latency = dash_table.DataTable(
        id="R1 Metadata Latency",
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
    Output('r1_table_multi_bucket_perf_stats', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')]
)
def gen_table_multi_bucket_perf_stats(n_clicks, branch, build_no):
    """
    Multiple Buckets Performance Statistics (Average) using HSBench and COSBench
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    final_rows = []
    col_names = ["Statistics", "4 KB", "100 KB", "1 MB", "5 MB", "36 MB", "64 MB", "128 MB",
                 "256 MB"]

    # retrieve overall hsbench data
    data = r1_perf_tables.get_hsbench_data(build_no)
    hs_bench_text = [["Hsbench", html.Br(), "1 Buckets", html.Br(), "1000 Objects", html.Br(),
                      "100 Sessions"],
                     ["Hsbench", html.Br(), "10 Buckets", html.Br(), "100 Objects", html.Br(),
                      "100 Sessions"],
                     ["Hsbench", html.Br(), "50 Buckets", html.Br(), "100 Objects", html.Br(),
                      "100 Sessions"]
                     ]
    index = 0
    for i in range(0, 18, 6):
        final_rows.extend(
            common.get_data_to_html_rows(data[i:i + 6], col_names, hs_bench_text[index], 6))
        index = index + 1

    # Retrieve data for cosbench
    data = r1_perf_tables.get_cosbench_data(build_no)
    cos_bench_text = [
        ["Cosbench", html.Br(), "1 Buckets", html.Br(), "1000 Objects", html.Br(), "100 Sessions"],
        ["Cosbench", html.Br(), "10 Buckets", html.Br(), "100 Objects", html.Br(),
         "100 Sessions"],
        ["Cosbench", html.Br(), "50 Buckets", html.Br(), "100 Objects", html.Br(),
         "100 Sessions"]
    ]
    index = 0
    for i in range(0, 18, 6):
        final_rows.extend(
            common.get_data_to_html_rows(data[i:i + 6], col_names, cos_bench_text[index], 6))
        index = index + 1

    col_names.insert(0, "Bench")
    table_headers = [html.Thead(html.Tr([html.Th(col) for col in col_names]))]
    table_body = [html.Tbody(final_rows)]
    table = dbc.Table(table_headers + table_body, bordered=True,
                      className="caption-Top col-xs-6",
                      hover=True,
                      responsive=True,
                      striped=True,
                      style=common.dict_style_cell)
    return table


@app.callback(
    Output('r1_table_bucket_ops_data', 'children'),
    [Input('submit_button', 'n_clicks'),
     Input('Bucket_Ops_Dropdown', 'value')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     ]
)
def get_table_bucket_ops_data(n_clicks, bucket_op, branch, build_no):
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate
    if bucket_op is None:
        bucket_op = "AvgLat"
    operations = ['INIT BCLR', 'INIT BDEL', 'BINIT', 'PUT', 'LIST', 'GET', 'DEL', 'BCLR', 'BDEL']
    object_size = ['4Kb', '100Kb', '1Mb', '5Mb', '36Mb', '64Mb', '128Mb', '256Mb']
    final_dict = {}
    bucket_obj_input = {'First': {'Bucket': 1, 'Object': 1000},  # 100 Sessions by default
                        'Second': {'Bucket': 10, 'Object': 1000},
                        'Third': {'Bucket': 50, 'Object': 5000}, }
    display_obj_input = {'First': {'Bucket': 1, 'Object': 1000},  # 100 Sessions by default
                         'Second': {'Bucket': 10, 'Object': 100},
                         'Third': {'Bucket': 50, 'Object': 100}, }
    html_data = []
    for keys in bucket_obj_input:
        final_dict["Operations"] = operations
        for ob_size in object_size:
            query = {'Build': build_no, 'Name': 'Hsbench', 'Object_Size': ob_size,
                     'Buckets': bucket_obj_input[keys]['Bucket'],
                     'Objects': bucket_obj_input[keys]['Object'], 'Sessions': 100}
            cursor = perf_api.find(query)
            try:
                doc = cursor[0]
                temp_data = []
                for i in range(0, 9):
                    try:
                        temp_data.append(r1_perf_tables.round_off(doc['Bucket_Ops'][i][bucket_op]))
                    except Exception as ex:
                        print("Exception {}".format(ex))
                        temp_data.append('-')
                final_dict[ob_size] = temp_data
            except Exception as ex:
                final_dict[ob_size] = '-' * 9
        df = pd.DataFrame(final_dict)
        span_txt = "{} Bucket,{} Objects,100 sessions".format(display_obj_input[keys]['Bucket'],
                                                              display_obj_input[keys]['Object'])
        html_data.extend(common.get_df_to_rows(df, span_txt, 9))

    col_name = ["Buckets", "Operations"]
    col_name.extend(operations)
    table_headers = [html.Thead(html.Tr([html.Th(col) for col in col_name]))]
    table_body = [html.Tbody(html_data)]
    table = dbc.Table(table_headers + table_body, bordered=True,
                      className="caption-Top col-xs-6",
                      hover=True,
                      responsive=True,
                      striped=True,
                      style=common.dict_style_cell)
    return table
