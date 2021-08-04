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

from Performance.schemas import statistics_column_headings, multiple_buckets_headings
# from threading import Thread
import pandas as pd
from Performance.schemas import *
from Performance.global_functions import get_distinct_keys, sort_object_sizes_list, get_db_details, keys_exists, round_off, check_empty_list
from Performance.mongodb_api import find_documents, count_documents
from Performance.styles import dict_style_header, dict_style_cell
import dash_table
import dash_html_components as html


def get_average_data(count, data, stat, subparam, multiplier):
    if count > 0 and keys_exists(data[0], stat):
        return round_off(data[0][stat][subparam] * multiplier)
    else:
        return "NA"


def get_data(count, data, stat, multiplier):
    if count > 0 and keys_exists(data[0], stat):
        return round_off(data[0][stat] * multiplier)
    else:
        return "NA"


def get_data_from_database(data):
    data_needed_for_query = data
    query = get_statistics_schema(data_needed_for_query)
    objects = get_distinct_keys(
        data_needed_for_query['release'], 'Object_Size', query)
    objects = sort_object_sizes_list(objects)

    if data_needed_for_query['name'] == 'S3bench':
        results = {
            'Object Sizes': statistics_column_headings
        }
    else:
        results = {
            'Object Sizes': multiple_buckets_headings
        }

    for obj in objects:
        get_benchmark_data(data_needed_for_query, results, obj)

    df = pd.DataFrame(results)
    df = df.T
    df.reset_index(inplace=True)
    df.columns = df.iloc[0]
    df = df[1:]

    return df


def get_benchmark_data(data_needed_for_query, results, obj):
    temp_data = []
    addedObjects = False
    operations = ["Write", "Read"]
    data_needed_for_query['objsize'] = obj

    if data_needed_for_query["name"] == 'S3bench':
        stats = ["Throughput", "IOPS", "Latency", "TTFB"]
    else:
        stats = ["Throughput", "IOPS", "Latency"]

    uri, db_name, db_collection = get_db_details(
        data_needed_for_query['release'])

    for operation in operations:
        data_needed_for_query['operation'] = operation

        query = get_complete_schema(data_needed_for_query)
        count = count_documents(query=query, uri=uri, db_name=db_name,
                                collection=db_collection)
        db_data = find_documents(query=query, uri=uri, db_name=db_name,
                                 collection=db_collection)

        if not addedObjects:
            try:
                num_objects = int(db_data[0]['Objects'])
            except IndexError:
                num_objects = "NA"
            except KeyError:
                num_objects = "NA"

            temp_data.append(num_objects)
            addedObjects = True

        for stat in stats:
            if data_needed_for_query["name"] == 'S3bench':
                if stat in ["Latency", "TTFB"]:
                    temp_data.append(get_average_data(
                        count, db_data, stat, "Avg", 1000))
                else:
                    temp_data.append(get_data(count, db_data, stat, 1))
            else:
                try:
                    temp_data.append(get_data(count, db_data, stat, 1))
                except TypeError:
                    temp_data.append(get_average_data(
                        count, db_data, stat, "Avg", 1))

    if not check_empty_list(temp_data):
        results[obj] = temp_data


def get_dash_table_from_dataframe(df, bench, column_id):
    if len(df) < 2:
        return html.P("Data is not Available.")
    else:
        if bench == 'metadata_s3bench':
            headings = [{'name': 'Operations', 'id': 'Statistics'},
                        {'name': 'Latency (ms)', 'id': '1KB'}
                        ]
        elif bench == 'bucketops_hsbench':
            headings = [
                {'name': 'Operations', 'id': 'Operations'},
                {'name': 'Average Latency', 'id': 'AvgLat'},
                {'name': 'Minimum Latency', 'id': 'MinLat'},
                {'name': 'Maximum Latency', 'id': 'MaxLat'},
                {'name': 'IOPS', 'id': 'Iops'},
                {'name': 'Throughput', 'id': 'Mbps'},
                {'name': 'Operations', 'id': 'Ops'},
                {'name': 'Execution Time', 'id': 'Seconds'},
            ]
        else:
            headings = [
                {'name': column, 'id': column} for column in list(df.columns)
            ]

        benchmark = dash_table.DataTable(
            id=f"{bench}_table",
            columns=headings,
            data=df.to_dict('records'),
            merge_duplicate_headers=True,
            sort_action="native",
            style_header=dict_style_header,
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#E5E4E2'},
                {'if': {'column_id': column_id}, 'backgroundColor': '#D8D8D8'}
            ],
            style_cell=dict_style_cell
        )
        return benchmark


def get_workload_headings(data):
    return html.H5(f"Data for {data['build']} build on branch {data['branch']} with {data['nodes']} nodes, {data['pfull']}% utilization having workload of {data['buckets']} bucket(s) and {data['sessions']} session(s).")


def get_metadata_latencies(data_needed_for_query):
    objects = ['1KB']

    results = {
        'Statistics': ['Add / Edit Object Tags', 'Read Object Tags',
                       'Read Object Metadata']
    }
    for obj in objects:
        temp_data = []
        operations = ["PutObjTag", "GetObjTag", "HeadObj"]

        uri, db_name, db_collection = get_db_details(
            data_needed_for_query['release'])

        for operation in operations:
            data_needed_for_query['operation'] = operation
            data_needed_for_query['objsize'] = obj
            query = get_complete_schema(data_needed_for_query)
            count = count_documents(query=query, uri=uri, db_name=db_name,
                                    collection=db_collection)
            db_data = find_documents(query=query, uri=uri, db_name=db_name,
                                     collection=db_collection)

            temp_data.append(get_average_data(
                count, db_data, "Latency", "Avg", 1000))

        if not check_empty_list(temp_data):
            results[obj] = temp_data

    if len(results) > 1:
        return pd.DataFrame(results)
    else:
        return pd.DataFrame()


def get_bucktops(data_needed_for_query):
    ops_modes = get_bucketops_modes()
    mode_indices = list(ops_modes.keys())

    bucket_ops = ['AvgLat', 'MinLat', 'MaxLat',
                  'Iops', 'Mbps', 'Ops', 'Seconds']
    data = {
        'Operations': bucketops_headings
    }
    uri, db_name, db_collection = get_db_details(
        data_needed_for_query['release'])

    data_needed_for_query['operation'] = 'Write'
    query = get_complete_schema(data_needed_for_query)
    count = count_documents(query=query, uri=uri, db_name=db_name,
                            collection=db_collection)
    db_data = find_documents(query=query, uri=uri, db_name=db_name,
                             collection=db_collection)
    try:
        results = db_data[0]["Bucket_Ops"]

        for bucket_operation in bucket_ops:
            temp_data = []
            for mode in mode_indices:
                if count > 0 and keys_exists(results[int(mode)], bucket_operation):
                    temp_data.append(
                        round_off(results[int(mode)][bucket_operation]))
                else:
                    temp_data.append("NA")

            if not check_empty_list(temp_data):
                data[bucket_operation] = temp_data
    except IndexError:
        return pd.DataFrame()
    except KeyError:
        return pd.DataFrame()

    if len(data) > 1:
        return pd.DataFrame(data)
    else:
        return pd.DataFrame()
