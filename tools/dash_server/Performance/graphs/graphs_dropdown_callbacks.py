"""graphs callbacks for performance for populating dropdown values"""
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

from Performance.global_functions import (
    get_dict_from_array,
    get_distinct_keys,
    sort_builds_list,
    sort_object_sizes_list,
    sort_sessions,
)
from Performance.styles import (
    style_dropdown_small_2,
    style_dropdown_medium,
    style_dropdown_large,
)
from common import app

# first dropdown


@app.callback(
    Output("graphs_branch_dropdown", "options"),
    Output("graphs_branch_dropdown", "value"),
    Output("graphs_branch_dropdown", "disabled"),
    Input("graphs_release_dropdown", "value"),
    State("graphs_branch_dropdown", "value"),
    prevent_initial_call=True,
)
def update_branches_dropdown(release_combined, current_value):
    """updates branches in default select dropdown"""
    options = None
    value = None
    disabled = False
    if release_combined is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        branches = get_distinct_keys(release, "Branch", {"OS": op_sys})
        if branches:
            options = get_dict_from_array(branches, False)
            if current_value in branches:
                value = current_value
            elif "stable" in branches:
                value = "stable"
            elif "cortx-1.0" in branches:
                value = "cortx-1.0"
            else:
                value = options[0]["value"]
            if len(options) == 1:
                disabled = True

        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_build_dropdown", "placeholder"),
    Output("graphs_build_compare_dropdown", "placeholder"),
    Input("graphs_filter_dropdown", "value"),
    prevent_initial_call=True,
)
def update_placeholder(xfilter):
    """updates placeholder for builds in default select dropdown"""
    placeholder = ""
    if not xfilter:  # pylint: disable=no-else-raise
        raise PreventUpdate
    elif xfilter == "Build":
        placeholder = "Build"
    else:
        placeholder = "Object Size"

    return [placeholder] * 2


@app.callback(
    Output("graphs_build_dropdown", "options"),
    Output("graphs_build_dropdown", "value"),
    Output("graphs_build_dropdown", "disabled"),
    Input("graphs_branch_dropdown", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_dropdown", "value"),
    State("graphs_build_dropdown", "value"),
    prevent_initial_call=True,
)
def update_options_dropdown(branch, xfilter, release_combined, current_value):
    """updates builds/ object sizes in default select dropdown"""
    versions = None
    value = None
    disabled = False
    if not all([xfilter, branch, release_combined]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        options = get_distinct_keys(release, xfilter, {"OS": op_sys, "Branch": branch})
        if options:
            if xfilter == "Build":
                builds = sort_builds_list(options)
                versions = get_dict_from_array(builds, True)
                if current_value in versions:
                    value = current_value
                else:
                    value = versions[0]["value"]
            else:
                obj_sizes = sort_object_sizes_list(options)
                versions = get_dict_from_array(obj_sizes, False)
                if current_value in versions:
                    value = current_value
                else:
                    value = versions[-1]["value"]

            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return versions, value, disabled


@app.callback(
    Output("graphs_nodes_dropdown", "options"),
    Output("graphs_nodes_dropdown", "value"),
    Output("graphs_nodes_dropdown", "disabled"),
    Input("graphs_build_dropdown", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_dropdown", "value"),
    State("graphs_branch_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_dropdown", "value"),
    prevent_initial_call=True,
)
def update_nodes_first(
    option1, xfilter, release_combined, branch, bench, current_value
):
    """updates nodes in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        nodes = get_distinct_keys(
            release,
            "Count_of_Servers",
            {"OS": op_sys, "Branch": branch, xfilter: option1, "Name": bench},
        )
        nodes = list(map(int, nodes))
        nodes.sort()
        if nodes:
            options = get_dict_from_array(nodes, False, "nodes")
            if current_value in nodes:
                value = current_value
            else:
                value = options[-1]["value"]
            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_clients_dropdown", "options"),
    Output("graphs_clients_dropdown", "value"),
    Output("graphs_clients_dropdown", "disabled"),
    Input("graphs_nodes_dropdown", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_dropdown", "value"),
    State("graphs_branch_dropdown", "value"),
    State("graphs_build_dropdown", "value"),
    State("graphs_clients_dropdown", "value"),
    prevent_initial_call=True,
)
def update_clients_first(
    nodes, xfilter, release_combined, branch, option1, current_value
):
    """updates clients in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not all( # pylint: disable=no-else-raise
        [xfilter, release_combined, branch, option1, nodes]
    ):
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        clients = get_distinct_keys(
            release,
            "Count_of_Clients",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Count_of_Servers": nodes,
            },
        )
        clients = list(map(int, clients))
        clients.sort()
        if nodes:
            options = get_dict_from_array(clients, False, "clients")
            if current_value in clients:
                value = current_value
            else:
                value = options[-1]["value"]
            if len(clients) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_pfull_dropdown", "options"),
    Output("graphs_pfull_dropdown", "value"),
    Output("graphs_pfull_dropdown", "disabled"),
    Input("graphs_clients_dropdown", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_dropdown", "value"),
    State("graphs_branch_dropdown", "value"),
    State("graphs_build_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_dropdown", "value"),
    State("graphs_pfull_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_percentfill_dropdown(
    clients, xfilter, release_combined, branch, option1, bench, nodes, current_value
):
    """updates percentage fill in cluster in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not all( # pylint: disable=no-else-raise
        [xfilter, branch, option1, bench, nodes, clients]
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        pfulls = get_distinct_keys(
            release,
            "Percentage_full",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
            },
        )
        if pfulls:
            options = get_dict_from_array(pfulls, False, "pfill")
            if current_value in pfulls:
                value = current_value
            else:
                value = options[0]["value"]
            if len(pfulls) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_custom_dropdown", "options"),
    Output("graphs_custom_dropdown", "value"),
    Output("graphs_custom_dropdown", "disabled"),
    Input("graphs_pfull_dropdown", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_dropdown", "value"),
    State("graphs_branch_dropdown", "value"),
    State("graphs_build_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_dropdown", "value"),
    State("graphs_clients_dropdown", "value"),
    State("graphs_custom_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_custom_dropdown(
    pfill,
    xfilter,
    release_combined,
    branch,
    option1,
    bench,
    nodes,
    clients,
    current_value,
):
    """updates custom field in default select dropdown"""
    options = None
    value = None
    disabled = False
    if ( not all([xfilter, branch, option1, bench, nodes, clients]) and pfill is None):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        custom = get_distinct_keys(
            release,
            "Custom",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
                "Percentage_full": pfill,
            },
        )
        if custom:
            options = get_dict_from_array(custom, False)
            if current_value in custom:
                value = current_value
            else:
                value = options[0]["value"]
            if len(custom) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_iteration_dropdown", "options"),
    Output("graphs_iteration_dropdown", "value"),
    Output("graphs_iteration_dropdown", "disabled"),
    Input("graphs_custom_dropdown", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_dropdown", "value"),
    State("graphs_branch_dropdown", "value"),
    State("graphs_build_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_dropdown", "value"),
    State("graphs_clients_dropdown", "value"),
    State("graphs_pfull_dropdown", "value"),
    State("graphs_iteration_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_iterations_dropdown(
    custom,
    xfilter,
    release_combined,
    branch,
    option1,
    bench,
    nodes,
    clients,
    pfill,
    current_value,
):
    """updates iterations of run in default select dropdown"""
    options = None
    value = None
    disabled = False
    if ( # pylint: disable=no-else-raise
        not all([xfilter, branch, option1, bench, nodes, clients, custom])
        and pfill is None
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        iterations = get_distinct_keys(
            release,
            "Iteration",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
                "Percentage_full": pfill,
                "Custom": custom,
            },
        )
        iterations.sort()
        if iterations:
            options = get_dict_from_array(iterations, True, "itrns")
            if current_value in iterations:
                value = current_value
            else:
                value = options[0]["value"]
            if len(iterations) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_sessions_dropdown", "options"),
    Output("graphs_sessions_dropdown", "value"),
    Output("graphs_sessions_dropdown", "disabled"),
    Input("graphs_iteration_dropdown", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_dropdown", "value"),
    State("graphs_branch_dropdown", "value"),
    State("graphs_build_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_dropdown", "value"),
    State("graphs_clients_dropdown", "value"),
    State("graphs_pfull_dropdown", "value"),
    State("graphs_custom_dropdown", "value"),
    State("graphs_sessions_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_sessions_dropdown(
    itrns,
    xfilter,
    release_combined,
    branch,
    option1,
    bench,
    nodes,
    clients,
    pfill,
    custom,
    current_value,
):
    """updates sessions in default select dropdown"""
    options = None
    value = None
    disabled = False
    if ( # pylint: disable=no-else-raise
        not all([xfilter, branch, option1, bench, nodes, clients, itrns, custom])
        and pfill is None
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        sessions = get_distinct_keys(
            release,
            "Sessions",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
                "Percentage_full": pfill,
                "Iteration": itrns,
                "Custom": custom,
            },
        )
        sessions.sort()
        if sessions:
            sessions = sort_sessions(sessions)
            options = get_dict_from_array(sessions, False, "sessions")
            if current_value in sessions:
                value = current_value
            elif 600 in sessions:
                value = 600
            else:
                value = options[-1]["value"]
            options.append({"label": "All", "value": "all"})
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_buckets_dropdown", "options"),
    Output("graphs_buckets_dropdown", "value"),
    Output("graphs_buckets_dropdown", "disabled"),
    Input("graphs_iteration_dropdown", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_dropdown", "value"),
    State("graphs_branch_dropdown", "value"),
    State("graphs_build_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_dropdown", "value"),
    State("graphs_clients_dropdown", "value"),
    State("graphs_pfull_dropdown", "value"),
    State("graphs_custom_dropdown", "value"),
    State("graphs_buckets_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_buckets_dropdown(
    itrns,
    xfilter,
    release_combined,
    branch,
    option1,
    bench,
    nodes,
    clients,
    pfill,
    custom,
    current_value,
):
    """updates buckets in default select dropdown"""
    options = None
    value = None
    disabled = False
    if ( # pylint: disable=no-else-raise
        not all([xfilter, branch, option1, bench, nodes, clients, itrns, custom])
        and pfill is None
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        buckets = get_distinct_keys(
            release,
            "Buckets",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
                "Percentage_full": pfill,
                "Iteration": itrns,
                "Custom": custom,
            },
        )
        buckets.sort()
        if buckets:
            options = get_dict_from_array(buckets, False, "buckets")
            if current_value in buckets:
                value = current_value
            else:
                value = options[0]["value"]
            if len(buckets) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


# second dropdown


@app.callback(
    [
        Output("graphs_release_compare_dropdown", "style"),
        Output("graphs_branch_compare_dropdown", "style"),
        Output("graphs_build_compare_dropdown", "style"),
        Output("graphs_nodes_compare_dropdown", "style"),
        Output("graphs_clients_compare_dropdown", "style"),
        Output("graphs_pfull_compare_dropdown", "style"),
        Output("graphs_iteration_compare_dropdown", "style"),
        Output("graphs_custom_compare_dropdown", "style"),
        Output("graphs_sessions_compare_dropdown", "style"),
        Output("graphs_buckets_compare_dropdown", "style"),
    ],
    Input("compare_flag", "value"),
)
def update_compare_dropdown_styles(flag):
    """shows 2nd set of dropdowns of comparison only when button is toggled"""
    return_val = [{"display": "None"}] * 10
    if flag:
        return_val = [
            style_dropdown_large,
            style_dropdown_small_2,
            style_dropdown_medium,
            style_dropdown_medium,
            style_dropdown_medium,
            style_dropdown_small_2,
            style_dropdown_small_2,
            style_dropdown_medium,
            style_dropdown_medium,
            style_dropdown_medium,
        ]

    return return_val


@app.callback(
    Output("graphs_branch_compare_dropdown", "options"),
    Output("graphs_branch_compare_dropdown", "value"),
    Output("graphs_branch_compare_dropdown", "disabled"),
    Input("graphs_release_compare_dropdown", "value"),
    Input("compare_flag", "value"),
    State("graphs_branch_compare_dropdown", "value"),
    prevent_initial_call=True,
)
def update_branches_dropdown_2(release_combined, flag, current_value):
    """updates branches in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag: # pylint: disable=no-else-raise
        raise PreventUpdate
    if release_combined is None:  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        branches = get_distinct_keys(release, "Branch", {"OS": op_sys})
        if branches:
            options = get_dict_from_array(branches, False)
            if current_value in branches:
                value = current_value
            elif "stable" in branches:
                value = "stable"
            elif "cortx-1.0" in branches:
                value = "cortx-1.0"
            else:
                value = options[0]["value"]
            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_build_compare_dropdown", "options"),
    Output("graphs_build_compare_dropdown", "value"),
    Output("graphs_build_compare_dropdown", "disabled"),
    Input("graphs_branch_compare_dropdown", "value"),
    Input("compare_flag", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_compare_dropdown", "value"),
    State("graphs_build_compare_dropdown", "value"),
    prevent_initial_call=True,
)
def update_options_dropdown_2(branch, flag, xfilter, release_combined, current_value):
    """updates build/ object sizes in comparison select dropdown"""
    versions = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, release_combined]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        options = get_distinct_keys(release, xfilter, {"OS": op_sys, "Branch": branch})
        if options:
            if xfilter == "Build":
                builds = sort_builds_list(options)
                versions = get_dict_from_array(builds, True)
                if current_value in builds:
                    value = current_value
                else:
                    value = versions[0]["value"]
            else:
                obj_sizes = sort_object_sizes_list(options)
                versions = get_dict_from_array(obj_sizes, False)
                if current_value in obj_sizes:
                    value = current_value
                else:
                    value = versions[0]["value"]

            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return versions, value, disabled


@app.callback(
    Output("graphs_nodes_compare_dropdown", "options"),
    Output("graphs_nodes_compare_dropdown", "value"),
    Output("graphs_nodes_compare_dropdown", "disabled"),
    Input("graphs_build_compare_dropdown", "value"),
    Input("compare_flag", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_compare_dropdown", "value"),
    State("graphs_branch_compare_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_compare_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_nodes_dropdown_2(
    option1, flag, xfilter, release_combined, branch, bench, current_value
):
    """updates nodes in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench]):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        nodes = get_distinct_keys(
            release,
            "Count_of_Servers",
            {"OS": op_sys, "Branch": branch, xfilter: option1, "Name": bench},
        )
        nodes = list(map(int, nodes))
        nodes.sort()
        if nodes:
            options = get_dict_from_array(nodes, False, "nodes")
            if current_value in nodes:
                value = current_value
            else:
                value = options[-1]["value"]
            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_clients_compare_dropdown", "options"),
    Output("graphs_clients_compare_dropdown", "value"),
    Output("graphs_clients_compare_dropdown", "disabled"),
    Input("graphs_nodes_compare_dropdown", "value"),
    Input("compare_flag", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_compare_dropdown", "value"),
    State("graphs_branch_compare_dropdown", "value"),
    State("graphs_build_compare_dropdown", "value"),
    State("graphs_clients_compare_dropdown", "value"),
    prevent_initial_call=True,
)
def update_clients_dropdown(
    nodes, flag, xfilter, release_combined, branch, option1, current_value
):
    """updates clientss in default select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all( # pylint: disable=no-else-raise
        [xfilter, release_combined, branch, option1, nodes]
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        clients = get_distinct_keys(
            release,
            "Count_of_Clients",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Count_of_Servers": nodes,
            },
        )
        clients = list(map(int, clients))
        clients.sort()
        if nodes:
            options = get_dict_from_array(clients, False, "clients")
            if current_value in clients:
                value = current_value
            else:
                value = options[-1]["value"]
            if len(clients) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_pfull_compare_dropdown", "options"),
    Output("graphs_pfull_compare_dropdown", "value"),
    Output("graphs_pfull_compare_dropdown", "disabled"),
    Input("graphs_clients_compare_dropdown", "value"),
    Input("compare_flag", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_compare_dropdown", "value"),
    State("graphs_branch_compare_dropdown", "value"),
    State("graphs_build_compare_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_compare_dropdown", "value"),
    State("graphs_pfull_compare_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_percentfill_dropdown_2(
    clients,
    flag,
    xfilter,
    release_combined,
    branch,
    option1,
    bench,
    nodes,
    current_value,
):
    """updates percent fill in cluster in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all( # pylint: disable=no-else-raise
        [xfilter, branch, option1, bench, nodes, clients]
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        pfulls = get_distinct_keys(
            release,
            "Percentage_full",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
            },
        )
        if pfulls:
            options = get_dict_from_array(pfulls, False, "pfill")
            if current_value in pfulls:
                value = current_value
            else:
                value = options[0]["value"]
            if len(pfulls) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_custom_compare_dropdown", "options"),
    Output("graphs_custom_compare_dropdown", "value"),
    Output("graphs_custom_compare_dropdown", "disabled"),
    Input("graphs_pfull_compare_dropdown", "value"),
    Input("compare_flag", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_compare_dropdown", "value"),
    State("graphs_branch_compare_dropdown", "value"),
    State("graphs_build_compare_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_compare_dropdown", "value"),
    State("graphs_clients_compare_dropdown", "value"),
    State("graphs_custom_compare_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_custom_dropdown_2(
    pfill,
    flag,
    xfilter,
    release_combined,
    branch,
    option1,
    bench,
    nodes,
    clients,
    current_value,
):
    """updates custom field in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if ( # pylint: disable=no-else-raise
        not all([xfilter, branch, option1, bench, nodes, clients]) and pfill is None
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        custom = get_distinct_keys(
            release,
            "Custom",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
                "Percentage_full": pfill,
            },
        )
        if custom:
            options = get_dict_from_array(custom, False)
            if current_value in custom:
                value = current_value
            else:
                value = options[0]["value"]
            if len(custom) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_iteration_compare_dropdown", "options"),
    Output("graphs_iteration_compare_dropdown", "value"),
    Output("graphs_iteration_compare_dropdown", "disabled"),
    Input("graphs_custom_compare_dropdown", "value"),
    Input("compare_flag", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_compare_dropdown", "value"),
    State("graphs_branch_compare_dropdown", "value"),
    State("graphs_build_compare_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_compare_dropdown", "value"),
    State("graphs_clients_compare_dropdown", "value"),
    State("graphs_pfull_compare_dropdown", "value"),
    State("graphs_iteration_compare_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_iterations_dropdown_2(
    custom,
    flag,
    xfilter,
    release_combined,
    branch,
    option1,
    bench,
    nodes,
    clients,
    pfill,
    current_value,
):
    """updates iterations of run in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if ( # pylint: disable=no-else-raise
        not all([xfilter, branch, option1, bench, nodes, clients, custom])
        and pfill is None
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        iterations = get_distinct_keys(
            release,
            "Iteration",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
                "Percentage_full": pfill,
                "Custom": custom,
            },
        )
        iterations.sort()
        if iterations:
            options = get_dict_from_array(iterations, False, "itrns")
            if current_value in iterations:
                value = current_value
            else:
                value = options[-1]["value"]
            if len(iterations) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_sessions_compare_dropdown", "options"),
    Output("graphs_sessions_compare_dropdown", "value"),
    Output("graphs_sessions_compare_dropdown", "disabled"),
    Input("graphs_iteration_compare_dropdown", "value"),
    Input("compare_flag", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_compare_dropdown", "value"),
    State("graphs_branch_compare_dropdown", "value"),
    State("graphs_build_compare_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_compare_dropdown", "value"),
    State("graphs_clients_compare_dropdown", "value"),
    State("graphs_pfull_compare_dropdown", "value"),
    State("graphs_custom_compare_dropdown", "value"),
    State("graphs_sessions_dropdown", "value"),
    State("graphs_sessions_compare_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_sessions_dropdown_2(
    itrns,
    flag,
    xfilter,
    release_combined,
    branch,
    option1,
    bench,
    nodes,
    clients,
    pfill,
    custom,
    sessions_first,
    current_value,
):
    """updates sessions in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if ( # pylint: disable=no-else-raise
        not all([xfilter, branch, option1, bench, nodes, clients, itrns, custom])
        and pfill is None
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        sessions = get_distinct_keys(
            release_combined.split("_")[0],
            "Sessions",
            {
                "OS": release_combined.split("_")[1],
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
                "Percentage_full": pfill,
                "Iteration": itrns,
                "Custom": custom,
            },
        )
        sessions.sort()
        if sessions:
            sessions = sort_sessions(sessions)
            options = get_dict_from_array(sessions, False, "sessions")
            if current_value in sessions:
                value = current_value
            elif sessions_first == "all":
                value = "all"
                disabled = True
            elif 600 in sessions:
                value = 600
            else:
                value = options[-1]["value"]
            options.append({"label": "All", "value": "all", "disabled": True})
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_buckets_compare_dropdown", "options"),
    Output("graphs_buckets_compare_dropdown", "value"),
    Output("graphs_buckets_compare_dropdown", "disabled"),
    Input("graphs_iteration_compare_dropdown", "value"),
    Input("compare_flag", "value"),
    State("graphs_filter_dropdown", "value"),
    State("graphs_release_compare_dropdown", "value"),
    State("graphs_branch_compare_dropdown", "value"),
    State("graphs_build_compare_dropdown", "value"),
    State("graphs_benchmark_dropdown", "value"),
    State("graphs_nodes_compare_dropdown", "value"),
    State("graphs_clients_compare_dropdown", "value"),
    State("graphs_pfull_compare_dropdown", "value"),
    State("graphs_custom_compare_dropdown", "value"),
    State("graphs_buckets_compare_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_buckets_dropdown_2(
    itrns,
    flag,
    xfilter,
    release_combined,
    branch,
    option1,
    bench,
    nodes,
    clients,
    pfill,
    custom,
    current_value,
):
    """updates buckets in comparison select dropdown"""
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if ( # pylint: disable=no-else-raise
        not all([xfilter, branch, option1, bench, nodes, clients, itrns, custom])
        and pfill is None
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        buckets = get_distinct_keys(
            release,
            "Buckets",
            {
                "OS": op_sys,
                "Branch": branch,
                xfilter: option1,
                "Name": bench,
                "Count_of_Servers": nodes,
                "Count_of_Clients": clients,
                "Percentage_full": pfill,
                "Iteration": itrns,
                "Custom": custom,
            },
        )
        buckets.sort()
        if buckets:
            options = get_dict_from_array(buckets, False, "buckets")
            if current_value in buckets:
                value = current_value
            else:
                value = options[0]["value"]
            if len(buckets) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output("graphs_obj_size_dropdown", "options"),
    Output("graphs_obj_size_dropdown", "value"),
    Output("graphs_obj_size_dropdown", "disabled"),
    Input("graphs_filter_dropdown", "value"),
    Input("graphs_release_dropdown", "value"),
    Input("graphs_branch_dropdown", "value"),
    Input("graphs_build_dropdown", "value"),
    Input("graphs_benchmark_dropdown", "value"),
    Input("graphs_sessions_dropdown", "value"),
    State("graphs_obj_size_dropdown", "value"),
    prevent_initial_call=True,
)  # pylint: disable=too-many-arguments
def update_object_size_dropdown(
    xfilter, release_combined, branch, build, bench, sessions, c_val
):
    """updates a object size dropdown when sessions all is chosen"""
    dict_options = None
    value = None
    disabled = False

    if not all( # pylint: disable=no-else-raise
        [xfilter, release_combined, branch, build, bench, sessions]
    ):  # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        if sessions == "all":
            if xfilter == "Build":
                options = get_distinct_keys(
                    release,
                    "Object_Size",
                    {"OS": op_sys, "Branch": branch, xfilter: build, "Name": bench},
                )
                options = sort_object_sizes_list(options)
            else:
                options = get_distinct_keys(
                    release,
                    "Build",
                    {"OS": op_sys, "Branch": branch, xfilter: build, "Name": bench},
                )
                options = sort_builds_list(options)

            if options:
                dict_options = get_dict_from_array(options, False)
                if c_val in options:
                    value = c_val
                else:
                    value = dict_options[-1]["value"]
                if len(options) == 1:
                    disabled = True
            else:
                raise PreventUpdate
        else:
            raise PreventUpdate

    return dict_options, value, disabled


@app.callback(
    Output("graphs_obj_size_dropdown", "style"),
    Input("graphs_sessions_dropdown", "value"),
)
def update_objsize_style(sessions):
    """hides the dropdown of obj size if sessions is not all"""
    style = {"display": "None"}

    if sessions == "all":
        style = style_dropdown_medium

    return style
