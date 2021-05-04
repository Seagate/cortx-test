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
from Performance.global_functions import benchmark_config


statistics_column_headings = ['Write Throughput (MBps)', 'Write IOPS', 'Write Latency (ms)', 'Write TTFB (ms)',
                              'Read Throughput (MBps)', 'Read IOPS', 'Read Latency (ms)', 'Read TTFB (ms)']

multiple_buckets_headings = ['Write Throughput (MBps)', 'Write IOPS', 'Write Latency (ms)',
                             'Read Throughput (MBps)', 'Read IOPS', 'Read Latency (ms)']

bucketops_headings = ['Create Buckets (BINIT)', 'Put Objects (PUT)', 'Listing Objects (LIST)', 'Get Objects (GET)',
                      'Delete Objects (DEL)', 'Clear Buckets (BCLR)', 'Delete Buckets (BDEL)']


@app.callback(
    [Output('statistics_s3bench_workload', 'children'),
     Output('statistics_s3bench_table', 'children')],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def s3bench_callback(n_clicks, release, branch, build, profile):
    workload_heading = html.H5("Workload: 100 Sessions, 1 Bucket")
    if n_clicks is None or branch is None or build is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        objects = fetch_configs_from_file(
            benchmark_config, 'S3bench', 'object_size')
        threads = []
        data = {
            'Object Sizes': statistics_column_headings
        }

        sessions = 100
        buckets = 1
        for obj in objects:
            temp = Thread(target=get_s3benchmark_data, args=(
                release, branch, build, obj, data, sessions, buckets, profile))
            temp.start()
            threads.append(temp)

        for thread in threads:
            thread.join()

        df_s3bench = pd.DataFrame(data)
        try:
            df_s3bench = df_s3bench[['Object Sizes'] + objects]
        except:
            pass
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
    else:
        return [workload_heading, None]


@app.callback(
    Output('statistics_metadata_table', 'children'),
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def metadata_callback(n_clicks, release, branch, build, profile):
    if n_clicks is None or branch is None or build is None or profile is None:
        raise PreventUpdate
        return None

    if n_clicks > 0:
        objects = fetch_configs_from_file(
            benchmark_config, 'S3bench', 'meta_data')
        threads = []
        data = {
            'Statistics': ['Add / Edit Object Tags', 'Read Object Tags',
                           'Read Object Metadata']
        }

        sessions = 100
        buckets = 1
        for obj in objects:
            temp = Thread(target=get_metadata_latencies, args=(
                release, branch, build, obj, data, sessions, buckets, profile))
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
    else:
        return None


def get_hsbench_workload_headings(html, sessions, buckets):
    return html.H5("Workload: {0} Sessions, {1} Buckets".format(sessions, buckets))


def get_cosbench_workload_headings(html, sessions, buckets):
    return html.H5("Workload: {0} Sessions, {1} Buckets".format(sessions, buckets))


def benchmark_global(bench, workload, release, branch, build, table_ID, profile):
    objects = fetch_configs_from_file(benchmark_config, bench, 'object_size')
    data = {
        'Object Sizes': multiple_buckets_headings
    }

    update_hsbench_callbacks(bench, workload, objects,
                             release, branch, build, Thread, data, profile)

    df_bench = pd.DataFrame(data)
    try:
        df_bench = df_bench[['Object Sizes'] + objects]
    except KeyError:
        pass
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
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def hsbench1_callback(n_clicks, release, branch, build, profile):
    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-1')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'])

    if n_clicks is None or branch is None or build is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        return [workload_heading, benchmark_global('Hsbench', workload, release, branch, build, 'hsbench-table-1', profile)]
    else:
        return [workload_heading, None]


@app.callback(
    [Output('statistics_hsbench_workload_2', 'children'),
     Output('statistics_hsbench_table_2', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def hsbench2_callback(n_clicks, release, branch, build, profile):
    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-2')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'])

    if n_clicks is None or branch is None or build is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        return [workload_heading, benchmark_global('Hsbench', workload, release, branch, build, 'hsbench-table-2', profile)]
    else:
        return [workload_heading, None]


@app.callback(
    [Output('statistics_hsbench_workload_3', 'children'),
     Output('statistics_hsbench_table_3', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def hsbench3_callback(n_clicks, release, branch, build, profile):
    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-3')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'])

    if n_clicks is None or branch is None or build is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        return [workload_heading, benchmark_global('Hsbench', workload, release, branch, build, 'hsbench-table-3', profile)]
    else:
        return [workload_heading, None]


@app.callback(
    [Output('statistics_cosbench_workload_1', 'children'),
     Output('statistics_cosbench_table_1', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def cosbench1_callback(n_clicks, release, branch, build, profile):
    workload = fetch_configs_from_file(
        benchmark_config, 'Cosbench', 'workload-1')
    workload_heading = get_cosbench_workload_headings(
        html, workload['sessions'], workload['buckets'])

    if n_clicks is None or branch is None or build is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        return [workload_heading, benchmark_global('Cosbench', workload, release, branch, build, 'cosbench-table-1', profile)]
    else:
        return [workload_heading, None]


@app.callback(
    [Output('statistics_cosbench_workload_2', 'children'),
     Output('statistics_cosbench_table_2', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def cosbench2_callback(n_clicks, release, branch, build, profile):
    workload = fetch_configs_from_file(
        benchmark_config, 'Cosbench', 'workload-2')
    workload_heading = get_cosbench_workload_headings(
        html, workload['sessions'], workload['buckets'])

    if n_clicks is None or branch is None or build is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        return [workload_heading, benchmark_global('Cosbench', workload, release, branch, build, 'cosbench-table-2', profile)]
    else:
        return [workload_heading, None]


@app.callback(
    [Output('statistics_cosbench_workload_3', 'children'),
     Output('statistics_cosbench_table_3', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def cosbench3_callback(n_clicks, release, branch, build, profile):
    workload = fetch_configs_from_file(
        benchmark_config, 'Cosbench', 'workload-3')
    workload_heading = get_cosbench_workload_headings(
        html, workload['sessions'], workload['buckets'])

    if n_clicks is None or branch is None or build is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        return [workload_heading, benchmark_global('Cosbench', workload, release, branch, build, 'cosbench-table-3', profile)]
    else:
        return [workload_heading, None]


def get_bucketops_everything(workload, release, branch, build, object_size, table_ID, profile):
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
        temp = Thread(target=get_bucketops, args=(object_size, benchmark_config, release, branch, build, 'write', mode_indices, operation,
                                                  workload['sessions'], workload['buckets'], data, profile))
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
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('bucketops_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def bucketops1_callback(n_clicks, release, branch, build, operation, profile):
    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-1')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'])

    if n_clicks is None or branch is None or build is None or operation is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        return [workload_heading, get_bucketops_everything(workload, release, branch, build, operation, 'bucketops-1', profile)]
    else:
        return [workload_heading, None]


@app.callback(
    [Output('statistics_bucketops_workload_2', 'children'),
     Output('statistics_bucketops_table_2', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('bucketops_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def bucketops2_callback(n_clicks, release, branch, build, operation, profile):
    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-2')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'])

    if n_clicks is None or branch is None or build is None or operation is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        return [workload_heading, get_bucketops_everything(workload, release, branch, build, operation, 'bucketops-2', profile)]
    else:
        return [workload_heading, None]


@app.callback(
    [Output('statistics_bucketops_workload_3', 'children'),
     Output('statistics_bucketops_table_3', 'children'), ],
    [Input('perf_submit_button', 'n_clicks'),
     Input('perf_release_dropdown', 'value'),
     Input('perf_branch_dropdown', 'value'),
     Input('perf_build_dropdown', 'value'),
     Input('bucketops_dropdown', 'value'),
     Input('profiles_options', 'value'),
     ],
    prevent_initial_call=True
)
def bucketops3_callback(n_clicks, release, branch, build, operation, profile):
    workload = fetch_configs_from_file(
        benchmark_config, 'Hsbench', 'workload-3')
    workload_heading = get_hsbench_workload_headings(
        html, workload['sessions'], workload['buckets'])

    if n_clicks is None or branch is None or build is None or operation is None or profile is None:
        raise PreventUpdate
        return [workload_heading, None]

    if n_clicks > 0:
        return [workload_heading, get_bucketops_everything(workload, release, branch, build, operation, 'bucketops-3', profile)]
    else:
        return [workload_heading, None]
