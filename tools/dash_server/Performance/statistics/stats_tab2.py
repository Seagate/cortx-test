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
import pandas as pd

from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
from common import app
from Performance.schemas import *
from Performance.backend import get_dash_table_from_dataframe
from Performance.global_functions import get_distinct_keys, sort_object_sizes_list, \
    get_db_details, round_off, check_empty_list
from Performance.mongodb_api import get_aggregate


def get_copy_object_data(data):
    """
    function for statistics tab to get data from database

    Args:
        data: dictionary needed for the query

    Returns:
        dataframe: Pandas dataframe with queried data
    """
    data_needed_for_query = data.copy()
    query = get_statistics_schema(data_needed_for_query)
    objects = get_distinct_keys(
        data_needed_for_query['release'], 'Object_Size', query)
    objects = sort_object_sizes_list(objects)

    results = {
        'Object Sizes': copyobj_headings
    }

    run_state_list = []
    for obj in objects:
        data_needed_for_query['objsize'] = obj
        temp_data, run_state = get_copy_object_benchmark_data(data_needed_for_query)
        if not check_empty_list(temp_data):
            run_state_list.append(run_state)
            results[obj] = temp_data

    df = pd.DataFrame(results)
    df = df.T
    df.reset_index(inplace=True)
    df.columns = df.iloc[0]
    df = df[1:]

    return df, run_state_list


def get_copy_object_benchmark_data(data_needed_for_query):  # pylint: disable=too-many-branches
    """
    Granularized function to query data from database for perf metrics

    Args:
        data: dictionary needed for the query

    Returns:
        results: dictionary to with appended data for this particular instance
    """
    temp_data = []
    run_state = "successful"
    added_objects = "NA"
    skipttfb = True
    operations = ["Read", "CopyObject", "Write"]


    uri, db_name, db_collection = get_db_details(
        data_needed_for_query['release'])

    for operation in operations:
        data_needed_for_query['operation'] = operation

        query = get_copyobject_schema(data_needed_for_query)
        group_query = {
            "_id": "null",
            "total_objs": { "$sum": "$Objects"},
            "sum_throughput": {"$sum": "$Throughput"},
            "sum_iops": {"$sum": "$IOPS"},
            "avg_lat": {"$avg": "$Latency"},
            "avg_lat_avg": {"$avg": "$Latency.Avg"},
            "run_state": { "$addToSet": "$Run_State"},
            "avg_ttfb_avg": {"$avg": "$TTFB.Avg"},
            "avg_ttfb_99p": {"$avg": "$TTFB.Avg"},
            }

        cursor = get_aggregate(query=query, group_query=group_query, uri=uri, db_name=db_name,
                        collection=db_collection)
        if not cursor:
            cursor = {
            "_id": "null", "total_objs": "NA", "sum_throughput": "NA", "sum_iops": "NA",
            "avg_lat": "NA", "avg_lat_avg": "NA", "run_state": "NA", "avg_ttfb_avg": "NA",
            "avg_ttfb_99p": "NA"}

        if cursor['total_objs'] != "NA":
            added_objects = cursor['total_objs']*2
        if 'failed' in cursor['run_state']:
            run_state = 'failed'

        temp_data.append(round_off(cursor['sum_throughput']))
        temp_data.append(round_off(cursor['sum_iops']))
        if data_needed_for_query["name"] == 'Hsbench':
            temp_data.append(round_off(cursor['avg_lat']))
        elif data_needed_for_query["name"] == 'S3bench':
            temp_data.append(round_off(cursor['avg_lat_avg']*1000))
            if skipttfb:
                temp_data.append(round_off(cursor['avg_ttfb_avg']*1000))
                temp_data.append(round_off(cursor['avg_ttfb_99p']*1000))
        else:
            temp_data.append(round_off(cursor['avg_lat']))

        skipttfb = False

    temp_data.insert(0, added_objects)
    return temp_data, run_state


@app.callback(
    Output('statistics_s3bench_table', 'children'),
    Input('perf_submit_button', 'n_clicks'),
    State('perf_release_dropdown', 'value'),
    State('perf_branch_dropdown', 'value'),
    State('perf_build_dropdown', 'value'),
    State('perf_nodes_dropdown', 'value'),
    State('perf_clients_dropdown', 'value'),
    State('perf_pfull_dropdown', 'value'),
    State('perf_iteration_dropdown', 'value'),
    State('perf_custom_dropdown', 'value'),
    State('perf_sessions_dropdown', 'value'),
    State('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_copy_obj_table(n_clicks, release_combined, branch, build, nodes, clients, pfull, itrns,
                   custom, sessions, buckets):
    table = None
    if not (all([
        release_combined, branch, build, nodes, clients, itrns, custom, n_clicks, sessions, buckets
    ])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        release = release_combined.split("_")[0]
        op_sys = release_combined.split("_")[1]
        data = {
            'release': release, 'OS': op_sys, 'build': build, 'branch': branch,
            'nodes': nodes, 'clients': clients, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'S3bench'
        }

        dataframe, states = get_copy_object_data(data)
        table = get_dash_table_from_dataframe(
            dataframe, 's3bench', 'Object Sizes', states)

    return table