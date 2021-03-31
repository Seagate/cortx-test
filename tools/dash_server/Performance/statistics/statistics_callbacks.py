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

import dash_table
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import pandas as pd
from threading import Thread
import dash_html_components as html

from Performance.statistics.statistics_functions import get_s3benchmark_data,\
    fetch_configs_from_file, get_metadata_latencies
from common import app
from Performance.styles import dict_style_header, dict_style_cell
from Performance.statistics.statistics_functions import update_hsbench_callbacks, get_dash_table, get_bucketops
from Performance.global_functions import get_dict_from_array, get_chain


benchmark_config = 'Performance/configs/benchmark.yml'
statistics_column_headings = ['Write Throughput (MBps)', 'Write Latency (ms)', 'Write TTFB (ms)', 'Write IOPS',
                              'Read Throughput (MBps)', 'Read Latency (ms)', 'Read IOPS', 'Read TTFB (ms)']

multiple_buckets_headings = ['Write Throughput (MBps)', 'Write Latency (ms)', 'Write IOPS',
                             'Read Throughput (MBps)', 'Read Latency (ms)', 'Read IOPS']

bucketops_headings = ['Create Buckets (BINIT)', 'Put Objects (PUT)', 'Listing Objects (LIST)', 'Get Objects (GET)',
                      'Delete Objects (DEL)', 'Clear Buckets (BCLR)', 'Delete Buckets (BDEL)']


@app.callback(
    Output('perf_branch_dropdown', 'options'),
    Input('perf_release_dropdown', 'value')
)
def update_branches_dropdown(release):
    versions = []
    if release == 'LR1':
        versions = [
            {'label': 'Cortx-1.0-Beta', 'value': 'beta'},
            {'label': 'Cortx-1.0', 'value': 'cortx1'},
            {'label': 'Custom', 'value': 'custom'},
            {'label': 'Main', 'value': 'main', 'disabled': True},
            {'label': 'Release', 'value': 'release'},
        ]
    elif release == 'LR2':
        versions = [
            {'label': 'Cortx-2.0-Beta', 'value': 'beta-2'},
            {'label': 'Cortx-1.0', 'value': 'cortx1'},
            {'label': 'Custom', 'value': 'custom', 'disabled': True},
            {'label': 'Release', 'value': 'release'},
        ]
    return versions


@app.callback(
    Output('perf_build_dropdown', 'options'),
    Input('perf_branch_dropdown', 'value')
)
def update_builds_dropdown(release):
    versions = None
    if release:
        builds = get_chain(release)
        versions = get_dict_from_array(builds, True)

    return versions


@app.callback(
    [Output('statistics_s3bench_workload', 'children'),
     Output('statistics_s3bench_table', 'children')],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     ]
)
def s3bench_callback(n_clicks, branch, build):
    if n_clicks is None or branch is None or build is None:
        raise PreventUpdate

    workload_heading = html.H5("Workload: 1 Bucket")
    objects = fetch_configs_from_file(
        benchmark_config, 'S3bench', 'object_size')
    threads = []
    data = {
        'Object Sizes': statistics_column_headings
    }

    for obj in objects:
        temp = Thread(target=get_s3benchmark_data, args=(build, obj, data))
        temp.start()
        threads.append(temp)

    for thread in threads:
        thread.join()

    df_s3bench = pd.DataFrame(data)
    df_s3bench = df_s3bench[['Object Sizes'] + objects]
    df_s3bench = df_s3bench.T
    df_s3bench.reset_index(inplace=True)
    df_s3bench.columns = df_s3bench.iloc[0]
    df_s3bench = df_s3bench[1:]

    columns = [
        {'name': column, 'id': column} for column in list(df_s3bench.columns)
    ]
    s3benchmark = dash_table.DataTable(
        id="s3bench_table",
        columns=columns,
        data=df_s3bench.to_dict('records'),
        merge_duplicate_headers=True,
        sort_action="native",
        style_header=dict_style_header,
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#E5E4E2'},
            {'if': {'column_id': 'Object Sizes'}, 'backgroundColor': '#D8D8D8'}
        ],
        style_cell=dict_style_cell
    )
    return [workload_heading, s3benchmark]


@app.callback(
    Output('statistics_metadata_table', 'children'),
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     ]
)
def metadata_callback(n_clicks, branch, build):
    if n_clicks is None or branch is None or build is None:
        raise PreventUpdate

    objects = fetch_configs_from_file(benchmark_config, 'S3bench', 'meta_data')
    threads = []
    data = {
        'Statistics': ['Add / Edit Object Tags', 'Read Object Tags',
                       'Read Object Metadata']
    }

    for obj in objects:
        temp = Thread(target=get_metadata_latencies, args=(build, obj, data))
        temp.start()
        threads.append(temp)

    for thread in threads:
        thread.join()

    df_metadata = pd.DataFrame(data)

    headings = [{'name': 'Operations', 'id': 'Statistics'},
                {'name': 'Latency (ms)', 'id': '1Kb'}
                ]
    metadata = dash_table.DataTable(
        id="metadata_table",
        columns=headings,
        data=df_metadata.to_dict('records'),
        merge_duplicate_headers=True,
        sort_action="native",
        style_header=dict_style_header,
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#E5E4E2'},
            {'if': {'column_id': 'Statistics'}, 'backgroundColor': '#D8D8D8'}
        ],
        style_cell=dict_style_cell
    )
    return metadata


def get_hsbench_workload_headings(html, sessions, buckets, objects):
    return html.H5("Workload: {0} Sessions, {1} Buckets, {2} Objects".format(sessions, buckets, objects))


def get_cosbench_workload_headings(html, sessions, buckets, objects):
    return html.H5("Workload: {0} Sessions, {1} Buckets, {2} Objects".format(sessions, buckets, objects*buckets))


def benchmark_global(bench, workload, branch, build, table_ID):
    objects = fetch_configs_from_file(benchmark_config, bench, 'object_size')
    data = {
        'Object Sizes': multiple_buckets_headings
    }

    update_hsbench_callbacks(bench, workload, objects, build, Thread, data)

    df_bench = pd.DataFrame(data)
    df_bench = df_bench[['Object Sizes'] + objects]
    df_bench = df_bench.T
    df_bench.reset_index(inplace=True)
    df_bench.columns = df_bench.iloc[0]
    df_bench = df_bench[1:]

    columns = [
        {'name': column, 'id': column} for column in list(df_bench.columns)
    ]

    hsbenchmark = get_dash_table(dash_table.DataTable, table_ID, columns,
                                 df_bench, dict_style_header, [
                                     {'if': {'row_index': 'odd'},
                                         'backgroundColor': '#E5E4E2'},
                                     {'if': {'column_id': 'Object Sizes'},
                                         'backgroundColor': '#D8D8D8'}
                                 ], dict_style_cell)

    return hsbenchmark


@app.callback(
    [Output('statistics_hsbench_workload_1', 'children'),
     Output('statistics_hsbench_table_1', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     ]
)
def hsbench1_callback(n_clicks, branch, build):
    if n_clicks is None or branch is None or build is None:
        raise PreventUpdate

    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-1')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'], workload['objects'])
    return [workload_heading, benchmark_global('Hsbench', workload, branch, build, 'hsbench-table-1')]


@app.callback(
    [Output('statistics_hsbench_workload_2', 'children'),
     Output('statistics_hsbench_table_2', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     ]
)
def hsbench2_callback(n_clicks, branch, build):
    if n_clicks is None or branch is None or build is None:
        raise PreventUpdate

    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-2')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'], workload['objects'])
    return [workload_heading, benchmark_global('Hsbench', workload, branch, build, 'hsbench-table-2')]


@app.callback(
    [Output('statistics_hsbench_workload_3', 'children'),
     Output('statistics_hsbench_table_3', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     ]
)
def hsbench3_callback(n_clicks, branch, build):
    if n_clicks is None or branch is None or build is None:
        raise PreventUpdate

    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-3')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'], workload['objects'])
    return [workload_heading, benchmark_global('Hsbench', workload, branch, build, 'hsbench-table-3')]


@app.callback(
    [Output('statistics_cosbench_workload_1', 'children'),
     Output('statistics_cosbench_table_1', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     ]
)
def cosbench1_callback(n_clicks, branch, build):
    if n_clicks is None or branch is None or build is None:
        raise PreventUpdate

    workload = fetch_configs_from_file(
        benchmark_config, 'Cosbench', 'workload-1')
    workload_heading = get_cosbench_workload_headings(
        html, workload['sessions'], workload['buckets'], workload['objects'])
    return [workload_heading, benchmark_global('Cosbench', workload, branch, build, 'cosbench-table-1')]


@app.callback(
    [Output('statistics_cosbench_workload_2', 'children'),
     Output('statistics_cosbench_table_2', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     ]
)
def cosbench2_callback(n_clicks, branch, build):
    if n_clicks is None or branch is None or build is None:
        raise PreventUpdate

    workload = fetch_configs_from_file(
        benchmark_config, 'Cosbench', 'workload-2')
    workload_heading = get_cosbench_workload_headings(
        html, workload['sessions'], workload['buckets'], workload['objects'])
    return [workload_heading, benchmark_global('Cosbench', workload, branch, build, 'cosbench-table-2')]


@app.callback(
    [Output('statistics_cosbench_workload_3', 'children'),
     Output('statistics_cosbench_table_3', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     ]
)
def cosbench3_callback(n_clicks, branch, build):
    if n_clicks is None or branch is None or build is None:
        raise PreventUpdate

    workload = fetch_configs_from_file(
        benchmark_config, 'Cosbench', 'workload-3')
    workload_heading = get_cosbench_workload_headings(
        html, workload['sessions'], workload['buckets'], workload['objects'])
    return [workload_heading, benchmark_global('Cosbench', workload, branch, build, 'cosbench-table-3')]


def get_bucketops_everything(workload, branch, build, object_size, table_ID):
    ops_modes = fetch_configs_from_file(benchmark_config, 'Hsbench', 'modes')
    mode_indices = list(ops_modes.keys())

    bucket_ops = ['AvgLat', 'MinLat', 'MaxLat',
                  'Iops', 'Mbps', 'Ops', 'Seconds']

    bucketops_columns = [
        {'name': 'Operations', 'id': 'Operations'},
        {'name': 'Average Latency', 'id': 'AvgLat'},
        {'name': 'Minimum Latency', 'id': 'MinLat'},
        {'name': 'Maximum Latency', 'id': 'MaxLat'},
        {'name': 'IOPS', 'id': 'Iops'},
        {'name': 'Throughput', 'id': 'Mbps'},
        {'name': 'Operations', 'id': 'Ops'},
        {'name': 'Execution Time', 'id': 'Seconds'},
    ]

    threads = []
    data = {
        'Operations': bucketops_headings
    }

    for operation in bucket_ops:
        temp = Thread(target=get_bucketops, args=(object_size, benchmark_config, build, 'write', mode_indices, operation,
                                                  workload['sessions'], workload['buckets'], workload['objects'], data))
        temp.start()
        threads.append(temp)

    for thread in threads:
        thread.join()

    df_bucketops = pd.DataFrame(data)

    bucketops = get_dash_table(dash_table.DataTable, table_ID, bucketops_columns,
                               df_bucketops, dict_style_header, [
                                   {'if': {'row_index': 'odd'},
                                       'backgroundColor': '#E5E4E2'},
                                   {'if': {'column_id': 'Operations'},
                                       'backgroundColor': '#D8D8D8'}
                               ], dict_style_cell)

    return bucketops


@app.callback(
    [Output('statistics_bucketops_workload_1', 'children'),
     Output('statistics_bucketops_table_1', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('bucketops_dropdown', 'value'),
     ]
)
def bucketops1_callback(n_clicks, branch, build, operation):
    if n_clicks is None or branch is None or build is None or operation is None:
        raise PreventUpdate

    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-1')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'], workload['objects'])
    return [workload_heading, get_bucketops_everything(workload, branch, build, operation, 'bucketops-1')]


@app.callback(
    [Output('statistics_bucketops_workload_2', 'children'),
     Output('statistics_bucketops_table_2', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('bucketops_dropdown', 'value'),
     ]
)
def bucketops2_callback(n_clicks, branch, build, operation):
    if n_clicks is None or branch is None or build is None or operation is None:
        raise PreventUpdate

    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-2')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'], workload['objects'])
    return [workload_heading, get_bucketops_everything(workload, branch, build, operation, 'bucketops-2')]


@app.callback(
    [Output('statistics_bucketops_workload_3', 'children'),
     Output('statistics_bucketops_table_3', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('bucketops_dropdown', 'value'),
     ]
)
def bucketops3_callback(n_clicks, branch, build, operation):
    if n_clicks is None or branch is None or build is None or operation is None:
        raise PreventUpdate

    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-3')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'], workload['objects'])
    return [workload_heading, get_bucketops_everything(workload, branch, build, operation, 'bucketops-3')]
