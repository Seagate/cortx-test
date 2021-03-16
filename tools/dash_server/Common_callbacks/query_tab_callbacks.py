""" Query tab callbacks."""
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License")
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
import dash_table
from http import HTTPStatus
import requests
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate

import common
import dash
from common import app
import pandas as  pd


def get_distinct_field_values(field_name):
    query_input = {"field": field_name, "query": {"latest": True}}
    query_input.update(common.credentials)
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query_input))

    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        field_values = json_response["result"]
        output = [
            {'label': val, 'value': val} for val in field_values if val.strip() != ""
        ]
        '''
        if common.DEBUG_PRINTS:
            print("Fetch {} value  for dropdown : {}".format(field_name, output))
        '''
        return output
    return None


# input fields and corresponding database fields
db_field_mapping = {"query_branch.value": "buildType", "query_build.value": "buildNo",
                    "query_system_type.value": "testPlanLabel",
                    "query_feature.value": "feature",
                    "query_test_plan.value": "testPlanID",
                    "query_test_execution.value": "testExecutionID",
                    "query_test_id.value": "testID",
                    "query_execution_type.value": "executionType",
                    "query_test_results.value": "testResult"}

column_names = {"buildType": "Build Type", "buildNo": "Build No", "testPlanID": "Test Plan ID",
                "testPlanLabel": "Test Plan Labels",
                "testExecutionID": "Test Execution ID",
                "testExecutionLabel": "Test Execution Labels", "testTeam": "Test Team",
                "feature": "Feature",
                "testID": "Test ID", "testName": "Test Name", "testType": "Test Type",
                "testResult": "Test Result", "logPath": "Log Path",
                "healthCheckResult": "Health Check Result",
                "testIDLabels": "Test ID Labels", "testTags": "Test Tags",
                "testStartTime": "Test Start Time", "testExecutionTime": "Test Execution Time",
                "executionType": "Execution Type", "issueIDs": "Issue IDs",
                "nodesHostname": "Node Hostnames", "noOfNodes": "No of Nodes",
                "clientHostname": "Client Hostname"}


@app.callback(
    Output('table_query_result', 'children'),
    [Input('query_result_button', 'n_clicks'),
     Input('query_branch', 'value'),
     Input('query_build', 'value'),
     Input('query_system_type', 'value'),
     Input('query_feature', 'value'),
     Input('query_test_plan', 'value'),
     Input('query_test_execution', 'value'),
     Input('query_test_id', 'value'),
     Input('query_execution_type', 'value'),
     Input('query_test_results', 'value'),
     Input('query_table_view', 'value')
     ]
)
def retrieve_query_results(n_clicks, *values):
    ctx = dash.callback_context
    # update only when getresults button is clicked.
    if ctx.triggered[0]['prop_id'] == 'query_result_button.n_clicks':
        query_input = {"latest": True}

        # Check valid inputs given before get result button
        input_found = False
        for input in ctx.inputs:
            if ctx.inputs[input] not in [None, [],
                                         [None]] and input != "query_result_button.n_clicks" \
                    and input != "query_table_view.value":
                input_found = True
                break
        if not input_found:
            return "No Inputs Selected!!!"

        # form query based on inputs
        for input in ctx.inputs:
            if ctx.inputs[input] not in [None, [],
                                         [None]] and input != "query_result_button.n_clicks" \
                    and input != "query_table_view.value":
                if len(ctx.inputs[input]) == 0:
                    pass
                elif len(ctx.inputs[input]) == 1:
                    query_input[db_field_mapping[input]] = ctx.inputs[input][0]
                else:
                    temp_list = []
                    for i in range(len(ctx.inputs[input])):
                        temp_dict = {db_field_mapping[input]: ctx.inputs[input][i]}
                        temp_list.append(temp_dict)
                    query_input['$or'] = temp_list
        query = {"query": query_input}
        query.update(common.credentials)
        print("Sending Query :{}".format(query))
        response = requests.request("GET", common.search_endpoint, headers=common.headers,
                                    data=json.dumps(query))
        # Fields to display
        data_from_db = {}
        if ctx.inputs["query_table_view.value"] == "detail":
            data_from_db = {"buildType": [], "buildNo": [], "testPlanID": [], "testPlanLabel": [],
                            "testExecutionID": [], "testExecutionLabel": [], "testTeam": [],
                            "feature": [],
                            "testID": [], "testName": [], "testType": [],
                            "testResult": [], "logPath": [], "healthCheckResult": [],
                            "testIDLabels": [], "testTags": [],
                            "testStartTime": [], "testExecutionTime": [],
                            "executionType": [], "issueIDs": [],
                            "nodesHostname": [], "noOfNodes": [], "clientHostname": []}
        else:
            data_from_db = {"buildType": [], "buildNo": [], "testPlanID": [], "testPlanLabel": [],
                            "testExecutionID": [],
                            "testID": [], "testName": [], "testType": [],
                            "testResult": [],
                            "testStartTime": [], "testExecutionTime": [],
                            "executionType": [], "issueIDs": [],
                            "nodesHostname": []}

        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            table_data = json_response["result"]

            for document in table_data:
                for db_key in data_from_db.keys():
                    if db_key in document and document[db_key] is not None:
                        data_from_db[db_key].append(document[db_key])
                    else:
                        data_from_db[db_key].append("-")

            df_query_output = pd.DataFrame(data_from_db)

            datatable_query_output = dash_table.DataTable(
                id="temp_table_query_result",
                columns=[{"name": column_names[i], "id": i, "deletable": True}
                         for i in df_query_output.columns],
                data=df_query_output.to_dict('records'),
                filter_action="native",
                page_action='native',
                page_current=0,
                page_size=20,
                export_format="csv",
                export_headers="display",
                # sort_action="native",
                style_cell_conditional=[{'if': {'column_id': 'testName'},
                                         'overflow': 'hidden',
                                         'textOverflow': 'ellipsis',
                                         'maxWidth': 350, },
                                        {'if': {'column_id': 'nodesHostname'},
                                         'overflow': 'hidden',
                                         'textOverflow': 'ellipsis',
                                         'maxWidth': 200, },
                                        {'if': {'column_id': 'testStartTime'},
                                         'overflow': 'hidden',
                                         'textOverflow': 'ellipsis',
                                         'maxWidth': 150, },
                                        ],

                style_cell={'textAlign': 'center', 'border': '1px solid black',
                            'font-size': '15px'},
                tooltip_data=[
                    {
                        column: {'value': str(value), 'type': 'markdown'}
                        for column, value in row.items()
                    } for row in df_query_output.to_dict('records')
                ],
                tooltip_duration=None,
                style_header=common.dict_style_header,
                style_header_conditional=[
                    {'whiteSpace': 'normal', 'height': 'auto', 'maxWidth': 150}],
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'}],
                style_table={
                    'width': '100%',
                    'overflowX': 'scroll',
                    'height': '50%',
                    'overflowY': 'auto'
                }
            )
            return datatable_query_output
    else:
        pass
    return []


def build_query(inputs):
    query_input = {"latest": True}
    for input in inputs:
        if inputs[input] not in [None, [None], []] and input != "query_result_button.n_clicks" \
                and input != "query_table_view.value":
            print("build query", inputs[input])
            if len(inputs[input]) == 0:
                pass
            elif len(inputs[input]) == 1:
                query_input[db_field_mapping[input]] = inputs[input][0]
            else:
                temp_list = []
                for i in range(len(inputs[input])):
                    temp_dict = {db_field_mapping[input]: inputs[input][i]}
                    temp_list.append(temp_dict)
                query_input['$or'] = temp_list
    print("Build query output : ", query_input)
    return query_input


@app.callback(
    [Output('query_branch', 'options')],
    [
        Input('query_build', 'value'),
        Input('query_system_type', 'value'),
        Input('query_feature', 'value'),
        Input('query_test_plan', 'value'),
        Input('query_test_execution', 'value'),
        Input('query_test_id', 'value'),
        Input('query_execution_type', 'value')
    ],
    [State('query_branch', 'value')]
)
def retrieve_query_branch(build, system_type, feature, test_plan, test_execution, test_id,
                          execution_type, current_val):
    '''
    Updates Branch values dynamically
    '''
    print("Query_branch :", current_val)
    ctx = dash.callback_context

    print("ctx inputs branch: ", ctx.inputs)
    if current_val not in [None, [None], []]:
        raise PreventUpdate

    # form query based on inputs
    query_input = build_query(ctx.inputs)
    query = {"field": "buildType", "query": query_input}
    query.update(common.credentials)
    print("Sending Query :{}".format(query))
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        branches = json_response["result"]
        options = [
            {'label': branch, 'value': branch} for branch in branches
        ]
        return [options]


@app.callback(
    [Output('query_build', 'options')],
    [
        Input('query_branch', 'value'),
        Input('query_system_type', 'value'),
        Input('query_feature', 'value'),
        Input('query_test_plan', 'value'),
        Input('query_test_execution', 'value'),
        Input('query_test_id', 'value'),
        Input('query_execution_type', 'value')
    ],
    [State('query_build', 'value')]
)
def retrieve_query_build(branch, system_type, feature, test_plan, test_execution, test_id,
                         execution_type, current_val):
    '''
    Updates Branch values dynamically
    '''

    # form query based on inputs
    if current_val not in [None, [None], []]:
        raise PreventUpdate

    ctx = dash.callback_context
    print("ctx inputs build :", ctx.inputs)
    query_input = build_query(ctx.inputs)
    query = {"field": "buildNo", "query": query_input}
    query.update(common.credentials)
    print("Sending Query :{}".format(query))
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        results = json_response["result"]
        options = [
            {'label': res_val, 'value': res_val} for res_val in results
        ]
        return [options]


@app.callback(
    [Output('query_system_type', 'options')],
    [
        Input('query_branch', 'value'),
        Input('query_build', 'value'),
        Input('query_feature', 'value'),
        Input('query_test_plan', 'value'),
        Input('query_test_execution', 'value'),
        Input('query_test_id', 'value'),
        Input('query_execution_type', 'value')
    ],
    [State('query_system_type', 'value')]
)
def retrieve_query_system_type(branch, build, feature, test_plan, test_execution, test_id,
                               execution_type, current_val):
    '''
    Updates Branch values dynamically
    '''

    if current_val not in [None, [None], []]:
        raise PreventUpdate

    # form query based on inputs
    ctx = dash.callback_context
    query_input = build_query(ctx.inputs)
    query = {"field": "testPlanLabel", "query": query_input}
    query.update(common.credentials)
    print("Sending Query :{}".format(query))
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        results = json_response["result"]
        options = [
            {'label': res_val, 'value': res_val} for res_val in results
        ]
        return [options]


@app.callback(
    [Output('query_feature', 'options')],
    [
        Input('query_branch', 'value'),
        Input('query_build', 'value'),
        Input('query_system_type', 'value'),
        Input('query_test_plan', 'value'),
        Input('query_test_execution', 'value'),
        Input('query_test_id', 'value'),
        Input('query_execution_type', 'value')
    ],
    [State('query_feature', 'value')]
)
def retrieve_query_feature(branch, build, system_type, test_plan, test_execution, test_id,
                           execution_type, current_val):
    '''
    Updates Branch values dynamically
    '''
    if current_val not in [None, [None], []]:
        raise PreventUpdate

    # form query based on inputs
    ctx = dash.callback_context
    query_input = build_query(ctx.inputs)
    query = {"field": "feature", "query": query_input}
    query.update(common.credentials)
    print("Sending Query :{}".format(query))
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        results = json_response["result"]
        options = [
            {'label': res_val, 'value': res_val} for res_val in results
        ]

        return [options]


@app.callback(
    [Output('query_test_plan', 'options')],
    [
        Input('query_branch', 'value'),
        Input('query_build', 'value'),
        Input('query_system_type', 'value'),
        Input('query_feature', 'value'),
        Input('query_test_execution', 'value'),
        Input('query_test_id', 'value'),
        Input('query_execution_type', 'value')
    ],
    [State('query_test_plan', 'value')]
)
def retrieve_query_test_plan(branch, build, system_type, test_plan, test_execution, test_id,
                             execution_type, current_val):
    '''
    Updates Branch values dynamically
    '''
    if current_val not in [None, [None], []]:
        raise PreventUpdate

    # form query based on inputs
    ctx = dash.callback_context
    query_input = build_query(ctx.inputs)
    query = {"field": "testPlanID", "query": query_input}
    query.update(common.credentials)
    print("Sending Query :{}".format(query))
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        results = json_response["result"]
        options = [
            {'label': res_val, 'value': res_val} for res_val in results
        ]
        return [options]


@app.callback(
    [Output('query_test_execution', 'options')],
    [
        Input('query_branch', 'value'),
        Input('query_build', 'value'),
        Input('query_system_type', 'value'),
        Input('query_feature', 'value'),
        Input('query_test_plan', 'value'),
        Input('query_test_id', 'value'),
        Input('query_execution_type', 'value')
    ],
    [State('query_test_execution', 'value')]
)
def retrieve_query_test_execution(branch, build, system_type, feature, test_plan, test_id,
                                  execution_type, current_val):
    '''
    Updates Branch values dynamically
    '''
    if current_val not in [None, [None], []]:
        raise PreventUpdate

    # form query based on inputs
    ctx = dash.callback_context
    query_input = build_query(ctx.inputs)
    query = {"field": "testExecutionID", "query": query_input}
    query.update(common.credentials)
    print("Sending Query :{}".format(query))
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        results = json_response["result"]
        options = [
            {'label': res_val, 'value': res_val} for res_val in results
        ]
        return [options]


@app.callback(
    [Output('query_test_id', 'options')],
    [
        Input('query_branch', 'value'),
        Input('query_build', 'value'),
        Input('query_system_type', 'value'),
        Input('query_feature', 'value'),
        Input('query_test_plan', 'value'),
        Input('query_test_execution', 'value'),
        Input('query_execution_type', 'value')
    ],
    [State('query_test_id', 'value')]
)
def retrieve_query_test_id(branch, build, system_type, feature, test_plan, test_execution,
                           execution_type, current_val):
    '''
    Updates Branch values dynamically
    '''
    if current_val not in [None, [None], []]:
        raise PreventUpdate

    # form query based on inputs
    ctx = dash.callback_context
    query_input = build_query(ctx.inputs)
    query = {"field": "testID", "query": query_input}
    query.update(common.credentials)
    print("Sending Query :{}".format(query))
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        results = json_response["result"]
        options = [
            {'label': res_val, 'value': res_val} for res_val in results
        ]
    return [options]


@app.callback(
    [Output('query_execution_type', 'options')],
    [
        Input('query_branch', 'value'),
        Input('query_build', 'value'),
        Input('query_system_type', 'value'),
        Input('query_feature', 'value'),
        Input('query_test_plan', 'value'),
        Input('query_test_execution', 'value'),
        Input('query_test_id', 'value')
    ],
    [State('query_execution_type', 'value')]
)
def retrieve_query_execution_type(branch, build, system_type, feature, test_plan, test_execution,
                                  test_id, current_val):
    '''
    Updates Branch values dynamically
    '''
    if current_val not in [None, [None], []]:
        raise PreventUpdate

    # form query based on inputs
    ctx = dash.callback_context
    query_input = build_query(ctx.inputs)
    query = {"field": "executionType", "query": query_input}
    query.update(common.credentials)
    print("Sending Query :{}".format(query))
    response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                data=json.dumps(query))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        results = json_response["result"]
        options = [
            {'label': res_val, 'value': res_val} for res_val in results
        ]
        return [options]
