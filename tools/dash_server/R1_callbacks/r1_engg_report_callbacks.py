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
import dash_table
import pandas as pd
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import common
from common import app
import mongodbAPIs as r1Api
import timingAPIs as timingAPIs


@app.callback(
    Output('r1_table_comp_summary', 'children'),
    [Input('submit_button', 'n_clicks'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     ]
)
def gen_table_comp_summary(n_clicks, branch, build_no):
    """
    Returns the component wise issues for current and previous builds.
    :param n_clicks: Input event
    :param branch: Build branch
    :param build_no: Build Number
    :return:
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    component_list = ["S3", "Provisioner", "CSM", "RAS", "Motr", "HA", "Locust", "Cosbench",
                      "Data Recovery", "Node Recovery"]
    cursor = r1Api.find({'info': 'build sequence'})
    build_list = cursor[0][branch]
    prev_build_no = build_list[build_list.index(build_no) - 1]
    build_no_list = [build_no, prev_build_no]
    # list of dictionary
    builds_details = []
    for build in build_no_list:
        pass_dict = {}
        fail_dict = {}
        for comp in component_list:
            pass_dict[comp] = r1Api.count_documents(
                {'build': build, 'deleted': False, 'testResult': 'PASS',
                 'testExecutionLabels': comp})
            fail_dict[comp] = r1Api.count_documents(
                {'build': build, 'deleted': False, 'testResult': 'FAIL',
                 'testExecutionLabels': comp})
        pass_dict["Total"] = sum(pass_dict.values())
        fail_dict["Total"] = sum(fail_dict.values())
        builds_details.append(pass_dict.values())
        builds_details.append(fail_dict.values())

    component_list.append("Total")
    df_comp_summary = pd.DataFrame({
        "Component": component_list,
        "current_pass": builds_details[0],
        "current_fail": builds_details[1],
        "previous_pass": builds_details[2],
        "previous_fail": builds_details[3]
    })
    comp_summary = dash_table.DataTable(
        id="comp_summary",
        columns=[
            {"name": ["Component", ""], "id": "Component"},
            {"name": [build_no, "Pass"], "id": "current_pass"},
            {"name": [build_no, "Fail"], "id": "current_fail"},
            {"name": [prev_build_no, "Pass"], "id": "previous_pass"},
            {"name": [prev_build_no, "Fail"], "id": "previous_fail"},
        ],
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
    [Input('submit_button', 'n_clicks'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value')
     ]
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

    return detail_reported_bugs


@app.callback(
    Output('r1_table_timing_summary', 'children'),
    [Input('submit_button', 'n_clicks'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value')
     ]
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

    cursor = r1Api.find({'info': 'build sequence'})
    build_list = cursor[0][branch]
    prev_build_no = build_list[build_list.index(build_no) - 1]
    build_no_list = [build_no, prev_build_no]
    timing_data = []
    for build in build_no_list:
        data_list = []
        for timing in timing_list:
            cursor = timingAPIs.find_distinct(timing, {'build': build})
            try:
                data = sum(cursor) / len(cursor)
            except Exception as ex:
                print("Exception received while calculating average{}".format(ex))
                data = "-"
            data_list.append(data)
        timing_data.append(data_list)

    data_timing_summary = {
        "Task": timing_list,
        build_no: timing_data[0],
        prev_build_no: timing_data[1]
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
