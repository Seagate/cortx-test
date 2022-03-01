"""Performance statistics callbacks for handling dropdowns"""
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

from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
from common import app

from Performance.global_functions import get_dict_from_array, get_distinct_keys, \
    sort_builds_list, sort_object_sizes_list, sort_sessions


@app.callback(
    Output('perf_branch_dropdown', 'options'),
    Output('perf_branch_dropdown', 'value'),
    Output('perf_branch_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    prevent_initial_call=True
)
def update_branches_dropdown(release_combined, current_value):
    options = None
    value = None
    disabled = False
    if release_combined is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        branches = get_distinct_keys(release, 'Branch', {'OS': op_sys})
        if branches:
            options = get_dict_from_array(branches, False, 'branch')
            if current_value in branches:
                value = current_value
            elif 'stable' in branches:
                value = 'stable'
            elif 'cortx-1.0' in branches:
                value = 'cortx-1.0'
            else:
                value = options[0]['value']
            if len(options) == 1:
                disabled = True

        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_build_dropdown', 'options'),
    Output('perf_build_dropdown', 'value'),
    Output('perf_build_dropdown', 'disabled'),
    Input('perf_branch_dropdown', 'value'),
    State('perf_release_dropdown', 'value'),
    State('perf_build_dropdown', 'value'),
    prevent_initial_call=True
)
def update_builds_dropdown(branch, release_combined, current_value):
    versions = None
    value = None
    disabled = False
    if not all([branch, release_combined]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        builds = get_distinct_keys(
            release, 'Build', {'OS': op_sys, 'Branch': branch})
        if builds:
            builds = sort_builds_list(builds)
            versions = get_dict_from_array(builds, True, 'build')
            if current_value in builds:
                value = current_value
            else:
                value = versions[0]['value']
            if len(builds) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return versions, value, disabled


@app.callback(
    Output('perf_nodes_dropdown', 'options'),
    Output('perf_nodes_dropdown', 'value'),
    Output('perf_nodes_dropdown', 'disabled'),
    Input('perf_build_dropdown', 'value'),
    State('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    State('perf_nodes_dropdown', 'value'),
    prevent_initial_call=True
)
def update_nodes_dropdown(build, release_combined, branch, current_value):
    options = None
    value = None
    disabled = False
    if not all([release_combined, branch, build]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        nodes = get_distinct_keys(release, 'Count_of_Servers', {'OS': op_sys,
                                  'Branch': branch, 'Build': build})
        nodes = list(map(int, nodes))
        nodes.sort()
        if nodes:
            options = get_dict_from_array(nodes, False, 'nodes')
            if current_value in nodes:
                value = current_value
            else:
                value = options[-1]['value']
            if len(nodes) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_clients_dropdown', 'options'),
    Output('perf_clients_dropdown', 'value'),
    Output('perf_clients_dropdown', 'disabled'),
    Input('perf_nodes_dropdown', 'value'),
    State('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    State('perf_build_dropdown', 'value'),
    State('perf_clients_dropdown', 'value'),
    prevent_initial_call=True
)
def update_clients_dropdown(nodes, release_combined, branch, build, current_value):
    options = None
    value = None
    disabled = False
    if not all([release_combined, branch, build, nodes]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        clients = get_distinct_keys(release, 'Count_of_Clients', {'OS': op_sys,
                                  'Branch': branch, 'Build': build, 'Count_of_Servers': nodes})
        clients = list(map(int, clients))
        clients.sort()
        if nodes:
            options = get_dict_from_array(clients, False, 'clients')
            if current_value in clients:
                value = current_value
            else:
                value = options[-1]['value']
            if len(clients) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_pfull_dropdown', 'options'),
    Output('perf_pfull_dropdown', 'value'),
    Output('perf_pfull_dropdown', 'disabled'),
    Input('perf_clients_dropdown', 'value'),
    State('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    State('perf_build_dropdown', 'value'),
    State('perf_nodes_dropdown', 'value'),
    State('perf_pfull_dropdown', 'value'),
    prevent_initial_call=True
)
def update_percentfill_dropdown(clients, release_combined, branch, build, nodes, current_value):
    options = None
    value = None
    disabled = False
    if not all([release_combined, branch, build, nodes, clients]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        pfulls = get_distinct_keys(release, 'Percentage_full', {
            'OS': op_sys, 'Branch': branch, 'Build': build, 'Count_of_Servers': nodes,
            'Count_of_Clients': clients })
        if pfulls:
            options = get_dict_from_array(pfulls, False, 'pfill')
            if current_value in pfulls:
                value = current_value
            else:
                value = options[0]['value']
            if len(pfulls) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_custom_dropdown', 'options'),
    Output('perf_custom_dropdown', 'value'),
    Output('perf_custom_dropdown', 'disabled'),
    Input('perf_pfull_dropdown', 'value'),
    State('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    State('perf_build_dropdown', 'value'),
    State('perf_nodes_dropdown', 'value'),
    State('perf_clients_dropdown', 'value'),
    State('perf_custom_dropdown', 'value'),
    prevent_initial_call=True
)
def update_custom_dropdown(pfull, release_combined, branch, build, nodes, clients, current_value):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes, clients]) and pfull is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        custom = get_distinct_keys(release, 'Custom', {
            'OS': op_sys, 'Branch': branch,
            'Build': build, 'Count_of_Servers': nodes, 'Count_of_Clients': clients,
            'Percentage_full': pfull})
        if custom:
            options = get_dict_from_array(custom, False)
            if current_value in custom:
                value = current_value
            else:
                value = options[0]['value']
            if len(custom) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_iteration_dropdown', 'options'),
    Output('perf_iteration_dropdown', 'value'),
    Output('perf_iteration_dropdown', 'disabled'),
    Input('perf_custom_dropdown', 'value'),
    State('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    State('perf_build_dropdown', 'value'),
    State('perf_nodes_dropdown', 'value'),
    State('perf_clients_dropdown', 'value'),
    State('perf_pfull_dropdown', 'value'),
    State('perf_iteration_dropdown', 'value'),
    prevent_initial_call=True
)
def update_iteration_dropdown(custom, release_combined, branch, build, nodes, clients,
    pfull, current_value):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes, custom, clients]) and pfull is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        iterations = get_distinct_keys(release, 'Iteration', {
            'OS': op_sys, 'Branch': branch, 'Build': build, 'Count_of_Servers': nodes,
            'Percentage_full': pfull, 'Count_of_Clients': clients, 'Custom': custom})
        iterations.sort()
        if iterations:
            options = get_dict_from_array(iterations, True, 'itrns')
            if current_value in iterations:
                value = current_value
            else:
                value = options[0]['value']
            if len(iterations) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_sessions_dropdown', 'options'),
    Output('perf_sessions_dropdown', 'value'),
    Output('perf_sessions_dropdown', 'disabled'),
    Input('perf_iteration_dropdown', 'value'),
    State('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    State('perf_build_dropdown', 'value'),
    State('perf_nodes_dropdown', 'value'),
    State('perf_clients_dropdown', 'value'),
    State('perf_pfull_dropdown', 'value'),
    State('perf_custom_dropdown', 'value'),
    State('perf_sessions_dropdown', 'value'),
    prevent_initial_call=True
)
def update_sessions_dropdown(itrns, release_combined, branch, build, nodes, clients, pfull, custom,
                                current_value):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes, itrns, clients]) and pfull is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        sessions = get_distinct_keys(release, 'Sessions', {
            'OS': op_sys, 'Branch': branch, 'Build': build, 'Count_of_Servers': nodes,
            'Count_of_Clients': clients, 'Percentage_full': pfull, 'Iteration': itrns,
            'Custom': custom
        })
        sessions.sort()
        if sessions:
            sessions = sort_sessions(sessions)
            options = get_dict_from_array(sessions, False, 'sessions')
            if current_value in sessions:
                value = current_value
            elif 600 in sessions:
                value = 600
            else:
                value = options[-1]['value']
            if len(sessions) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_buckets_dropdown', 'options'),
    Output('perf_buckets_dropdown', 'value'),
    Output('perf_buckets_dropdown', 'disabled'),
    Input('perf_sessions_dropdown', 'value'),
    State('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    State('perf_build_dropdown', 'value'),
    State('perf_nodes_dropdown', 'value'),
    State('perf_clients_dropdown', 'value'),
    State('perf_pfull_dropdown', 'value'),
    State('perf_custom_dropdown', 'value'),
    State('perf_iteration_dropdown', 'value'),
    State('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_buckets_dropdown(sessions, release_combined, branch, build, nodes, clients,
                     pfull, custom, itrns, current_value):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes, clients, itrns, sessions]) and pfull is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        buckets = get_distinct_keys(release, 'Buckets', {
            'OS': op_sys, 'Branch': branch, 'Build': build, 'Count_of_Servers': nodes,
            'Count_of_Clients': clients, 'Percentage_full': pfull, 'Iteration': itrns,
            'Custom': custom, 'Sessions': sessions
        })
        buckets = list(map(int, buckets))
        buckets.sort()
        if buckets:
            options = get_dict_from_array(buckets, False, 'buckets')
            if current_value in buckets:
                value = current_value
            else:
                value = options[0]['value']
            if len(buckets) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_bucketops_dropdown', 'options'),
    Output('perf_bucketops_dropdown', 'value'),
    Output('perf_bucketops_dropdown', 'disabled'),
    Input('perf_buckets_dropdown', 'value'),
    State('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    State('perf_build_dropdown', 'value'),
    State('perf_nodes_dropdown', 'value'),
    State('perf_clients_dropdown', 'value'),
    State('perf_pfull_dropdown', 'value'),
    State('perf_iteration_dropdown', 'value'),
    State('perf_custom_dropdown', 'value'),
    State('perf_sessions_dropdown', 'value'),
    State('perf_bucketops_dropdown', 'value'),
    prevent_initial_call=True
)
def update_bucketops_dropdown(buckets, release_combined, branch, build, nodes, clients,
 pfull, itrns, custom, sessions, current_value):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes, itrns, sessions, buckets, clients]) and pfull is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        objsizes = get_distinct_keys(release, 'Object_Size', {
            'OS': op_sys, 'Branch': branch, 'Build': build, 'Count_of_Servers': nodes,
            'Count_of_Clients': clients, 'Percentage_full': pfull, 'Iteration': itrns,
            'Custom': custom, 'Name': 'Hsbench', 'Buckets': buckets, 'Sessions': sessions
        })
        if objsizes:
            objsizes = sort_object_sizes_list(objsizes)
            options = get_dict_from_array(objsizes, False)
            if current_value in objsizes:
                value = current_value
            else:
                value = options[-1]['value']
            if len(objsizes) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled
