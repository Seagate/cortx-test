"""Performance Statistics tab data callbacks"""
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
from common import app
from Performance.backend import *


@app.callback(
    Output('statistics_workload', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
)
def update_workload(release_combined, branch, build, nodes,
                    pfull, itrns, custom, n_clicks, sessions, buckets):
    workload = None
    if not (all([
        release_combined, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets
    ])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        data = {
            'release': release, 'OS': op_sys, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'S3bench'
        }

        workload = get_workload_headings(data)

    return workload


@app.callback(
    Output('statistics_s3bench_table', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_s3bench(release_combined, branch, build, nodes, pfull, itrns,
                   custom, n_clicks, sessions, buckets):
    table = None
    if not (all([
        release_combined, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets
    ])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        data = {
            'release': release, 'OS': op_sys, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'S3bench'
        }

        dataframe, states = get_data_for_stats(data)
        table = get_dash_table_from_dataframe(
            dataframe, 's3bench', 'Object Sizes', states)

    return table


@app.callback(
    Output('statistics_metadata_table', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_metadata(release_combined, branch, build, nodes,
                    pfull, itrns, custom, n_clicks, sessions, buckets):
    table = None
    if not (all([
        release_combined, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets
    ])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        data = {
            'release': release, 'OS': op_sys, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'S3bench',
        }
        dataframe, run_states = get_metadata_latencies(data)
        table = get_dash_table_from_dataframe(
            dataframe, 'metadata_s3bench', 'Statistics', run_states)

    return table


@app.callback(
    Output('statistics_hsbench_table', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_hsbench(release_combined, branch, build, nodes,
                   pfull, itrns, custom, n_clicks, sessions, buckets):
    table = None
    if not (all([release_combined, branch, build, nodes,
                 itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        data = {
            'release': release, 'OS': op_sys, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'Hsbench'
        }
        dataframe, states = get_data_for_stats(data)
        table = get_dash_table_from_dataframe(
            dataframe, 'hsbench', 'Object Sizes', states)

    return table


@app.callback(
    Output('statistics_bucketops_table', 'children'),
    [Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('perf_nodes_dropdown', 'value'),
     Input('perf_pfull_dropdown', 'value'),
     Input('perf_iteration_dropdown', 'value'),
     Input('perf_custom_dropdown', 'value'),
     Input('perf_submit_button', 'n_clicks'),
     Input('perf_sessions_dropdown', 'value'),
     Input('perf_buckets_dropdown', 'value'),
     Input('perf_bucketops_dropdown', 'value')],
    prevent_initial_call=True
)
def update_bucketops(release_combined, branch, build, nodes,
                     pfull, itrns, custom, n_clicks, sessions, buckets, objsize):
    table = None
    if not (all([release_combined, branch, build, nodes,
                 itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        data = {
            'release': release_combined.split("_")[0], 'OS': release_combined.split("_")[1],
            'build': build, 'branch': branch, 'nodes': nodes,
            'pfull': pfull, 'itrns': itrns, 'custom': custom, 'buckets': buckets,
            'sessions': sessions, 'name': 'Hsbench', 'objsize': objsize
        }
        dataframe, run_states = get_bucktops(data)
        table = get_dash_table_from_dataframe(
            dataframe, 'bucketops_hsbench', 'Operations', run_states)

    return table


@app.callback(
    Output('statistics_cosbench_table', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_cosbench(release_combined, branch, build, nodes,
                    pfull, itrns, custom, n_clicks, sessions, buckets):
    table = None
    if not (all([release_combined, branch, build, nodes,
                 itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        data = {
            'release': release, 'OS': op_sys, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'Cosbench'
        }
        dataframe, states = get_data_for_stats(data)
        table = get_dash_table_from_dataframe(
            dataframe, 'cosbench', 'Object Sizes', states)

    return table
