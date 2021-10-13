"""graphs callbacks for performance for populating dropdown values"""
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

from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate

from Performance.global_functions import get_dict_from_array,\
    get_distinct_keys, sort_builds_list, sort_object_sizes_list, sort_sessions
from Performance.styles import style_dropdown_small, style_dropdown_small_2, style_dropdown_medium
from common import app

# first dropdown


@app.callback(
    Output('graphs_branch_dropdown', 'options'),
    Output('graphs_branch_dropdown', 'value'),
    Output('graphs_branch_dropdown', 'disabled'),
    Input('graphs_release_dropdown', 'value'),
    prevent_initial_call=True
)
def update_branches_dropdown(release):
    """updates branches in default select dropdown"""
    options = None
    value = None
    disabled = False
    if release is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        branches = get_distinct_keys(release, 'Branch', {})
        if branches:
            options = get_dict_from_array(branches, False)
            if 'Release' in branches:
                value = 'Release'
            elif 'stable' in branches:
                value = 'stable'
            elif 'custom' in branches:
                value = 'custom'
            else:
                value = options[0]['value']
            if len(options) == 1:
                disabled = True

        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_build_dropdown', 'placeholder'),
    Output('graphs_build_compare_dropdown', 'placeholder'),
    Input('graphs_filter_dropdown', 'value'),
    prevent_initial_call=True
)
def update_placeholder(xfilter):
    """updates palceholder for builds in default select dropdown"""
    placeholder = ""
    if not xfilter:  # pylint: disable=no-else-raise
        raise PreventUpdate
    elif xfilter == 'Build':
        placeholder = "Build"
    else:
        placeholder = "Object Size"

    return [placeholder]*2


@app.callback(
    Output('graphs_build_dropdown', 'options'),
    Output('graphs_build_dropdown', 'value'),
    Output('graphs_build_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    prevent_initial_call=True
)
def update_options_dropdown(xfilter, release, branch):
    """updates builds/ object sizes in default select dropdown"""
    versions = None
    value = None
    disabled = False
    if not all([xfilter, branch, release]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        options = get_distinct_keys(release, xfilter, {'Branch': branch})
        if options:
            if xfilter == 'Build':
                builds = sort_builds_list(options)
                versions = get_dict_from_array(builds, True)
                value = versions[0]['value']
            else:
                obj_sizes = sort_object_sizes_list(options)
                versions = get_dict_from_array(obj_sizes, False)
                value = versions[0]['value']

            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return versions, value, disabled


@app.callback(
    Output('graphs_nodes_dropdown', 'options'),
    Output('graphs_nodes_dropdown', 'value'),
    Output('graphs_nodes_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    prevent_initial_call=True
)
def update_nodes_first(xfilter, release, branch, option1, bench):
    """updates nodes in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        nodes = get_distinct_keys(release, 'Count_of_Servers', {
                                  'Branch': branch, xfilter: option1, 'Name': bench})
        nodes = list(map(int, nodes))
        if nodes:
            options = get_dict_from_array(nodes, False, 'nodes')
            value = options[0]['value']
            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_pfull_dropdown', 'options'),
    Output('graphs_pfull_dropdown', 'value'),
    Output('graphs_pfull_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_percentfill_dropdown(xfilter, release, branch, option1, bench, nodes):
    """updates percentage fill in cluster in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        pfulls = get_distinct_keys(release, 'Percentage_full', {
            'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes})
        if pfulls:
            options = get_dict_from_array(pfulls, False, 'pfill')
            value = options[0]['value']
            if len(pfulls) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_custom_dropdown', 'options'),
    Output('graphs_custom_dropdown', 'value'),
    Output('graphs_custom_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    Input('graphs_pfull_dropdown', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_custom_dropdown(xfilter, release, branch, option1, bench, nodes, pfill):
    """updates custom field in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes]) and pfill is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        custom = get_distinct_keys(release, 'Custom', {
            'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes,
            'Percentage_full': pfill})
        if custom:
            options = get_dict_from_array(custom, False)
            value = options[0]['value']
            if len(custom) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_iteration_dropdown', 'options'),
    Output('graphs_iteration_dropdown', 'value'),
    Output('graphs_iteration_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    Input('graphs_pfull_dropdown', 'value'),
    Input('graphs_custom_dropdown', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_iterations_dropdown(xfilter, release, branch, option1, bench, nodes, pfill, custom):
    """updates iterations of run in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes, custom]) and pfill is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        iterations = get_distinct_keys(release, 'Iteration',
                                       {'Branch': branch, xfilter: option1, 'Name': bench,
                                        'Count_of_Servers': nodes, 'Percentage_full': pfill,
                                        'Custom': custom})
        if iterations:
            options = get_dict_from_array(iterations, False, 'itrns')
            value = options[0]['value']
            if len(iterations) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_sessions_dropdown', 'options'),
    Output('graphs_sessions_dropdown', 'value'),
    Output('graphs_sessions_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    Input('graphs_pfull_dropdown', 'value'),
    Input('graphs_iteration_dropdown', 'value'),
    Input('graphs_custom_dropdown', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_sessions_dropdown(xfilter, release, branch, option1, bench, nodes, pfill, itrns, custom):
    """updates sessions in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes, itrns, custom]) and pfill is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        sessions = get_distinct_keys(release, 'Sessions', {
            'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes,
            'Percentage_full': pfill, 'Iteration': itrns, 'Custom': custom})
        if sessions:
            sessions = sort_sessions(sessions)
            options = get_dict_from_array(sessions, False, 'sessions')
            value = options[0]['value']
            options.append({'label': 'All', 'value': 'all'})
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_buckets_dropdown', 'options'),
    Output('graphs_buckets_dropdown', 'value'),
    Output('graphs_buckets_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    Input('graphs_pfull_dropdown', 'value'),
    Input('graphs_iteration_dropdown', 'value'),
    Input('graphs_custom_dropdown', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_buckets_dropdown(xfilter, release, branch, option1, bench,
                            nodes, pfill, itrns, custom):
    """updates buckets in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes, itrns, custom]) and pfill is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        buckets = get_distinct_keys(release, 'Buckets', {
            'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes,
            'Percentage_full': pfill, 'Iteration': itrns, 'Custom': custom})
        if buckets:
            options = get_dict_from_array(buckets, False, 'buckets')
            value = options[0]['value']
            if len(buckets) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


# second dropdown


@app.callback(
    [Output('graphs_release_compare_dropdown', 'style'),
     Output('graphs_branch_compare_dropdown', 'style'),
     Output('graphs_build_compare_dropdown', 'style'),
     Output('graphs_nodes_compare_dropdown', 'style'),
     Output('graphs_pfull_compare_dropdown', 'style'),
     Output('graphs_iteration_compare_dropdown', 'style'),
     Output('graphs_custom_compare_dropdown', 'style'),
     Output('graphs_sessions_compare_dropdown', 'style'),
     Output('graphs_buckets_compare_dropdown', 'style')],
    Input('compare_flag', 'value'),
)
def update_compare_dropdown_styles(flag):
    """shows 2nd set of dropdowns of comparison only when button is toggled"""
    return_val = [{'display': 'None'}]*9
    if flag:
        return_val = [
            style_dropdown_small, style_dropdown_small_2, style_dropdown_medium,
            style_dropdown_medium, style_dropdown_small_2, style_dropdown_small_2,
            style_dropdown_medium, style_dropdown_medium, style_dropdown_medium
        ]

    return return_val


@app.callback(
    Output('graphs_branch_compare_dropdown', 'options'),
    Output('graphs_branch_compare_dropdown', 'value'),
    Output('graphs_branch_compare_dropdown', 'disabled'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_branches_dropdown_2(release, flag):
    """updates branches in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if release is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        branches = get_distinct_keys(release, 'Branch', {})
        if branches:
            options = get_dict_from_array(branches, False)
            if 'Release' in branches:
                value = 'Release'
            elif 'stable' in branches:
                value = 'stable'
            elif 'custom' in branches:
                value = 'custom'
            else:
                value = options[0]['value']
            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_build_compare_dropdown', 'options'),
    Output('graphs_build_compare_dropdown', 'value'),
    Output('graphs_build_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_options_dropdown_2(xfilter, release, branch, flag):
    """updates build/ object sizes in comparison select dropdown"""
    versions = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, release]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        options = get_distinct_keys(release, xfilter, {'Branch': branch})
        if options:
            if xfilter == 'Build':
                builds = sort_builds_list(options)
                versions = get_dict_from_array(builds, True)
                value = versions[0]['value']
            else:
                obj_sizes = sort_object_sizes_list(options)
                versions = get_dict_from_array(obj_sizes, False)
                value = versions[0]['value']

            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return versions, value, disabled


@app.callback(
    Output('graphs_nodes_compare_dropdown', 'options'),
    Output('graphs_nodes_compare_dropdown', 'value'),
    Output('graphs_nodes_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_nodes_dropdown_2(xfilter, release, branch, option1, bench, flag):
    """updates nodes in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        nodes = get_distinct_keys(release, 'Count_of_Servers', {
                                  'Branch': branch, xfilter: option1, 'Name': bench})
        nodes = list(map(int, nodes))
        if nodes:
            options = get_dict_from_array(nodes, False, 'nodes')
            value = options[0]['value']
            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_pfull_compare_dropdown', 'options'),
    Output('graphs_pfull_compare_dropdown', 'value'),
    Output('graphs_pfull_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_percentfill_dropdown_2(xfilter, release, branch, option1, bench, nodes, flag):
    """updates percent fill in cluster in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        pfulls = get_distinct_keys(release, 'Percentage_full', {
            'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes})
        if pfulls:
            options = get_dict_from_array(pfulls, False, 'pfill')
            value = options[0]['value']
            if len(pfulls) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_custom_compare_dropdown', 'options'),
    Output('graphs_custom_compare_dropdown', 'value'),
    Output('graphs_custom_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('graphs_pfull_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_custom_dropdown_2(xfilter, release, branch, option1, bench, nodes, pfill, flag):
    """updates custom field in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes]) and pfill is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        custom = get_distinct_keys(release, 'Custom', {
            'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes,
            'Percentage_full': pfill})
        if custom:
            options = get_dict_from_array(custom, False)
            value = options[0]['value']
            if len(custom) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_iteration_compare_dropdown', 'options'),
    Output('graphs_iteration_compare_dropdown', 'value'),
    Output('graphs_iteration_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('graphs_pfull_compare_dropdown', 'value'),
    Input('graphs_custom_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_iterations_dropdown_2(xfilter, release, branch, option1, bench, nodes, pfill,
                                 custom, flag):
    """updates iterations of run in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes, custom]) and pfill is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        iterations = get_distinct_keys(release, 'Iteration', {
            'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes,
            'Percentage_full': pfill, 'Custom': custom})
        if iterations:
            options = get_dict_from_array(iterations, False, 'itrns')
            value = options[0]['value']
            if len(iterations) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_sessions_compare_dropdown', 'options'),
    Output('graphs_sessions_compare_dropdown', 'value'),
    Output('graphs_sessions_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('graphs_pfull_compare_dropdown', 'value'),
    Input('graphs_iteration_compare_dropdown', 'value'),
    Input('graphs_custom_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    Input('graphs_sessions_dropdown', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_sessions_dropdown_2(xfilter, release, branch, option1, bench,
                               nodes, pfill, itrns, custom, flag, sessions_first):
    """updates sessions in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes, itrns, custom]) and pfill is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        sessions = get_distinct_keys(release, 'Sessions', {
            'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes,
            'Percentage_full': pfill, 'Iteration': itrns, 'Custom': custom})
        if sessions:
            sessions = sort_sessions(sessions)
            options = get_dict_from_array(sessions, False, 'sessions')
            if sessions_first == 'all':
                value = 'all'
                disabled = True
            else:
                value = options[0]['value']
            options.append({'label': 'All', 'value': 'all', 'disabled': True})
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_buckets_compare_dropdown', 'options'),
    Output('graphs_buckets_compare_dropdown', 'value'),
    Output('graphs_buckets_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('graphs_pfull_compare_dropdown', 'value'),
    Input('graphs_iteration_compare_dropdown', 'value'),
    Input('graphs_custom_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_buckets_dropdown_2(xfilter, release, branch, option1, bench, nodes,
                              pfill, itrns, custom, flag):
    """updates buckets in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes, itrns, custom]) and pfill is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        buckets = get_distinct_keys(release, 'Buckets', {
            'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes,
            'Percentage_full': pfill, 'Iteration': itrns, 'Custom': custom})
        if buckets:
            options = get_dict_from_array(buckets, False, 'buckets')
            value = options[0]['value']
            if len(buckets) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_obj_size_dropdown', 'options'),
    Output('graphs_obj_size_dropdown', 'value'),
    Output('graphs_obj_size_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_sessions_dropdown', 'value'),
    prevent_initial_call=True
)  # pylint: disable=too-many-arguments
def update_object_size_dropdown(xfilter, release, branch, build, bench, sessions):
    """updates a object size dropdown when sessions all is chosen"""
    dict_options = None
    value = None
    disabled = False

    if not all([xfilter, release, branch, build, bench, sessions]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        if sessions == 'all':
            if xfilter == 'Build':
                options = get_distinct_keys(release, 'Object_Size', {
                    'Branch': branch, xfilter: build, 'Name': bench})
                options = sort_object_sizes_list(options)
            else:
                options = get_distinct_keys(release, 'Build', {
                    'Branch': branch, xfilter: build, 'Name': bench})
                options = sort_builds_list(options)

            if options:
                dict_options = get_dict_from_array(options, False)
                value = dict_options[0]['value']
                if len(options) == 1:
                    disabled = True
            else:
                raise PreventUpdate
        else:
            raise PreventUpdate

    return dict_options, value, disabled


@app.callback(
    Output('graphs_obj_size_dropdown', 'style'),
    Input('graphs_sessions_dropdown', 'value'),
)
def update_objsize_style(sessions):
    """hides the dropdown of obj size if sessions is not all"""
    style = {'display': 'None'}

    if sessions == 'all':
        style = style_dropdown_medium

    return style
