""" Main page callbacks."""
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
from http import HTTPStatus
import requests
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
import common
from common import app
import mongodbAPIs as r1Api


@app.callback(
    [Output('branch_dropdown', 'options')],
    [Input('version_dropdown', 'value')]
)
def fetch_branch_for_dropdown(value):
    """
    Fetch branch based on the version(R1/R2)
    :param value:
    :return:
    """
    if not value:
        raise PreventUpdate
    if value == "LR1":
        # Hardcoded values used for R1
        output = [
            {'label': 'Cortx-1.0-Beta', 'value': 'beta'},
            {'label': 'Cortx-1.0', 'value': 'cortx-1-*'},
        ]
        if common.DEBUG_PRINTS:
            print("Fetch branch for dropdown : {}".format(output))
        return [output]
    else:
        # fetch for R2
        query_input = {"field": "buildType", "query": {"latest": True}}
        query_input.update(common.credentials)
        response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            branches = json_response["result"]
            output = [
                {'label': branch, 'value': branch} for branch in branches
            ]
            if common.DEBUG_PRINTS:
                print("Fetch branch for dropdown : {}".format(output))
            return [output]
    return None


@app.callback(
    [Output('build_no_dropdown', 'options')],
    [Input('branch_dropdown', 'value')],
    [State('version_dropdown', 'value')],
)
def fetch_build_for_dropdown(branch, version):
    """
    Fetch the build no based on the branch/version
    :param version: R1/R2
    :param branch : Branch name ex: Beta/Release
    :return:
    """
    if not version or not branch:
        raise PreventUpdate

    if version == "LR1":
        cursor = r1Api.find({'info': 'build sequence R1'})
        list1 = cursor[0][branch]
        result = [ele for ele in reversed(list1)]
        output = [
            {'label': build, 'value': build} for build in result
        ]
        return [output]
    else:
        query_input = {"query": {"buildType": branch, "latest": True}, "field": "buildNo"}
        query_input.update(common.credentials)
        response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            all_builds = json_response["result"]
            output = [
                {'label': build_no, 'value': build_no} for build_no in all_builds
            ]
            if common.DEBUG_PRINTS:
                print("Fetch build for dropdown : result : {}".format(output))
            return [output]
    return None


@app.callback(
    [Output('test_system_dropdown', 'options')],
    [Input('version_dropdown', 'value'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value')]
)
def fetch_test_system_for_dropdown(version, branch, build_no):
    """
    Fetch system type for the required version(r1/r2),branch and build no
    :param version:R1/R2
    :param branch: Branch name ex: Release/Beta
    :param build_no:
    :return:
    """
    if not (version and build_no and branch):
        raise PreventUpdate

    if version == "LR1":
        # test system not applicable for R1
        raise PreventUpdate
    else:
        # testPlanLabel corresponds to the system type: for ex: isolated, near full system
        query_input = {"query": {"buildType": branch, "buildNo": build_no, "latest": True},
                       "field": "testPlanLabel"}
        query_input.update(common.credentials)
        response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            label = json_response["result"]
            output = [
                {'label': sys_type, 'value': sys_type} for sys_type in label
            ]
            return [output]
    return None


@app.callback(
    [Output('test_team_dropdown', 'options')],
    [Input('version_dropdown', 'value'),
     Input('branch_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value')]
)
def fetch_team_for_dropdown(version, branch, build_no, system_type):
    """
    Fetch the testing teams for version, build_no and testing system type
    :param version:Product version R1/R2
    :param branch: Branch name Release/Beta etc
    :param build_no: Build no
    :param system_type: System type : Isolated/Regular etc
    :return:
    """
    if not (version and branch and build_no and system_type):
        raise PreventUpdate

    if version == "LR1":
        # test team not applicable for R1
        raise PreventUpdate
    else:
        # testPlanLabel corresponds to the system type: for ex: isolated, near full system
        query_input = {
            "query": {"buildType": branch, "buildNo": build_no, "testPlanLabel": system_type,
                      "latest": True},
            "field": "testTeam"}
        query_input.update(common.credentials)
        response = requests.request("GET", common.distinct_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            teams = json_response["result"]
            output = [
                {'label': team, 'value': team} for team in teams
            ]
            return [output]
    return None


@app.callback(
    Output('toggle_visibility', 'style'),
    [Input('version_dropdown', 'value')]
)
def toggle_dropdown_visibility(version):
    """
    Hide system type and test team drop down for R1
    :param version:
    :return:
    """
    if not version:
        raise PreventUpdate
    if version == "LR1":
        return {'display': 'none'}
    else:
        return None
