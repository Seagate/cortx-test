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
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import common
from common import app


@app.callback(
    [Output('build_no_dropdown', 'options')],
    [Input('version_dropdown', 'value')],
)
def fetch_build_for_dropdown(value):
    """
    Fetch the build no based on the branch/version
    :param value:
    :return:
    """
    if not value:
        raise PreventUpdate
    if value in ["Beta", "Release"]:
        query_input = {"query": {"buildType": value}, "projection": {"buildNo": "true"}}
        query_input.update(common.credentials)
        response = requests.request("GET", common.search_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            all_builds = []
            for each in json_response["result"]:
                all_builds.append(each["buildNo"])
            all_builds = list(set(all_builds))
            output = [
                {'label': build_no, 'value': build_no} for build_no in all_builds
            ]
            if common.DEBUG_PRINTS:
                print("Fetch build for dropdown : result : {}".format(output))
            return [output]
    return None


@app.callback(
    [Output('test_system_dropdown', 'options')],
    [Input('version_dropdown', 'value')],
    [Input('build_no_dropdown', 'value')]
)
def fetch_test_system_for_dropdown(version, build_no):
    """
    Fetch system type for the required branch/version and build no
    :param version:
    :param build_no:
    :return:
    """
    if not (version and build_no):
        raise PreventUpdate
    if version in ["Beta", "Release"]:
        # testPlanLabel corresponds to the system type: for ex: isolated, near full system
        query_input = {"query": {"buildType": version, "buildNo": build_no},
                       "projection": {"testPlanLabel": "true"}}
        query_input.update(common.credentials)
        response = requests.request("GET", common.search_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            label = []
            for each in json_response["result"]:
                if each["testPlanLabel"]:
                    label.append(each["testPlanLabel"])
            label = list(set(label))
            output = [
                {'label': sys_type, 'value': sys_type} for sys_type in label
            ]
            return [output]
    return None


@app.callback(
    [Output('test_team_dropdown', 'options')],
    [Input('version_dropdown', 'value')],
    [Input('build_no_dropdown', 'value')],
    [Input('test_system_dropdown', 'value')]
)
def fetch_team_for_dropdown(version, build_no, system_type):
    """
    Fetch the testing teams for version, build_no and testing system type
    :param version:
    :param build_no:
    :param system_type:
    :return:
    """
    if not (version and build_no and system_type):
        raise PreventUpdate
    if version in ["Beta", "Release"]:
        # testPlanLabel corresponds to the system type: for ex: isolated, near full system
        query_input = {
            "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": system_type},
            "projection": {"testTeam": "true"}}
        query_input.update(common.credentials)
        response = requests.request("GET", common.search_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            teams = []
            for each in json_response["result"]:
                teams.append(each["testTeam"])
            teams = list(set(teams))
            output = [
                {'label': team, 'value': team} for team in teams
            ]
            return [output]
    return None
