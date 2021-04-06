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

from Performance.global_functions import get_db_details, keys_exists, round_off, makeconfig
from Performance.mongodb_api import find_documents, count_documents


def get_performance_metrics(release: str, branch: str, build: str, object_size: str, bench: str, operation: str,
                            sessions: int = None, buckets: int = None, objects: int = None):
    """need to add release and version logic"""
    uri, db_name, db_collection = get_db_details(release)

    if sessions:
        query = {'Branch': branch, 'Build': build, 'Name': bench, 'Object_Size': object_size,
                 'Operation': operation, 'Sessions': sessions, 'Buckets': buckets, 'Objects': objects}
    else:
        query = {'Branch': branch, 'Build': build, 'Name': bench,
                 'Object_Size': object_size, 'Operation': operation}

    count = count_documents(query=query, uri=uri, db_name=db_name,
                            collection=db_collection)
    db_data = find_documents(query=query, uri=uri, db_name=db_name,
                             collection=db_collection)

    return count, db_data


def fetch_configs_from_file(benchmark_config, bench, prop):
    config = makeconfig(benchmark_config)
    return config[bench][prop]


def get_average_data(count, data, stat, subparam, multiplier):
    if count > 0 and keys_exists(data[0], stat, subparam):
        return round_off(data[0][stat][subparam] * multiplier)
    else:
        return "NA"


def get_data(count, data, stat, multiplier):
    if count > 0 and keys_exists(data[0], stat):
        return round_off(data[0][stat] * multiplier)
    else:
        return "NA"


def get_s3benchmark_data(release, branch, build, object_size, data):
    temp_data = []
    operations = ["Write", "Read"]
    for operation in operations:
        count, db_data = get_performance_metrics(
            release, branch, build, object_size, 'S3bench', operation)
        stats = ["Throughput", "Latency", "IOPS", "TTFB"]

        for stat in stats:
            if stat in ["Latency", "TTFB"]:
                temp_data.append(get_average_data(
                    count, db_data, stat, "Avg", 1000))
            else:
                temp_data.append(get_data(count, db_data, stat, 1))

    data[object_size] = temp_data


def get_metadata_latencies(release, branch, build, object_size, data):
    temp_data = []
    operations = ["PutObjTag", "GetObjTag", "HeadObj"]

    for operation in operations:
        count, db_data = get_performance_metrics(
            release, branch, build, object_size, 'S3bench', operation)
        temp_data.append(get_average_data(
            count, db_data, "Latency", "Avg", 1000))

    data[object_size] = temp_data


def get_hsbenchmark_data(release, branch, build, object_size, sessions, buckets, objects, data):
    temp_data = []
    operations = ["write", "read"]
    for operation in operations:
        count, db_data = get_performance_metrics(
            release, branch, build, object_size, 'Hsbench', operation, sessions, buckets, objects)
        stats = ["Throughput", "Latency", "IOPS"]

        for stat in stats:
            temp_data.append(get_data(count, db_data, stat, 1))

    data[object_size] = temp_data


def get_cosbenchmark_data(release, branch, build, object_size, sessions, buckets, objects, data):
    temp_data = []
    operations = ["write", "read"]
    for operation in operations:
        count, db_data = get_performance_metrics(
            release, branch, build, object_size, 'Cosbench', operation, sessions, buckets, objects)
        stats = ["Throughput", "Latency", "IOPS"]

        for stat in stats:
            if stat == "Latency":
                temp_data.append(get_average_data(
                    count, db_data, stat, "Avg", 1))
            else:
                temp_data.append(get_data(count, db_data, stat, 1))

    data[object_size] = temp_data


def update_hsbench_callbacks(bench, workload, objects, release, branch, build, Thread, data):
    threads = []

    if bench == 'Hsbench':
        target = get_hsbenchmark_data
    elif bench == 'Cosbench':
        target = get_cosbenchmark_data

    for obj in objects:
        temp = Thread(target=target, args=(release, branch, build, obj, workload['sessions'],
                                           workload['buckets'], workload['objects'], data))
        temp.start()
        threads.append(temp)

    for thread in threads:
        thread.join()


def get_dash_table(DataTable, table_id, columns, dataframe, header_style, conditional_style, cell_Style):
    table = DataTable(
        id=table_id,
        columns=columns,
        data=dataframe.to_dict('records'),
        merge_duplicate_headers=True,
        sort_action="native",
        style_header=header_style,
        style_data_conditional=conditional_style,
        style_cell=cell_Style
    )
    return table


def get_bucketops(object_size, benchmark_config, release, branch, build, operation, modes, bucket_operation,
                  sessions, buckets, objects, data):

    count, db_data = get_performance_metrics(release, branch, build, object_size, 'Hsbench',
                                             operation, sessions, buckets, objects)
    results = db_data[0]['Bucket_Ops']

    temp_data = []
    for mode in modes:
        if count > 0 and keys_exists(results[mode], bucket_operation):
            temp_data.append(round_off(results[mode][bucket_operation]))
        else:
            temp_data.append("NA")

    data[bucket_operation] = temp_data
