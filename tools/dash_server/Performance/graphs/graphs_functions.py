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

from Performance.global_functions import benchmark_config, get_chain
from Performance.statistics.statistics_functions import fetch_configs_from_file,\
    get_data, get_average_data


def get_performance_metrics(build: str, object_size: str, bench: str, operation: str,
                            sessions: int = None, buckets: int = None, objects: int = None, version='release', release='R1'):
    """need to add release and version logic"""
    uri, db_name, db_collection = get_db_details()

    if sessions:
        query = {'Build': build, 'Name': bench, 'Object_Size': object_size,
                 'Operation': operation, 'Sessions': sessions, 'Buckets': buckets, 'Objects': objects}
    else:
        query = {'Build': build, 'Name': bench,
                 'Object_Size': object_size, 'Operation': operation}

    count = count_documents(query=query, uri=uri, db_name=db_name,
                            collection=db_collection)
    db_data = find_documents(query=query, uri=uri, db_name=db_name,
                             collection=db_collection)

    return count, db_data


def get_structure_trace(Scatter, operation, metrics, option, x_axis, y_data):
    trace = Scatter(
        name='{} {} - {}'.format(operation, metrics, option),
        x=x_axis,
        y=y_data,
        hovertemplate='<br>%{y} MBps<br>' +
        '<b>{} - {}</b><extra></extra>'.format(
            operation, option),
    )
    return trace


def get_operations(bench, operation_opt):
    if bench == 'S3bench':
        if operation_opt == 'both':
            return ['Read', 'Write']
        else:
            return operation_opt.capitalize()

    if operation_opt == 'both':
        return ['read', 'write']
    else:
        return operation_opt


def get_options(option1, option2):
    if option2:
        return [option1, option2]
    else:
        return [option1]


def data_routine(results, build, object_size, bench, operation, param,
                 buckets=None, objects=None, sessions=None, subparam=None):

    if subparam:
        try:
            count, data = get_performance_metrics(build, object_size, bench,
                                                  operation, sessions, buckets, objects)
            results.append(get_average_data(
                count, data, param, subparam, 1000))

        except KeyError:
            results.append(None)
    else:
        try:
            count, data = get_performance_metrics(build, object_size,
                                                  bench, operation, sessions, buckets, objects)
            results.append(get_data(count, data, param, 1))

        except KeyError:
            results.append(None)


def get_configs(bench, configs):
    if configs:
        workload = fetch_configs_from_file(
            benchmark_config, bench, 'workload-{}'.format(configs))
        return workload['buckets'], workload['objects'], workload['sessions']

    else:
        return None, None, None


def get_objsizewise_data(build, bench, configs, operation, param, subparam=None):
    data = []
    objsize_list = fetch_configs_from_file(
        benchmark_config, bench, 'object_size')

    buckets, objects, sessions = get_configs(bench, configs)

    for object_size in objsize_list:
        data_routine(data, build, object_size, bench, operation,
                     param, buckets, objects, sessions, subparam)

    data_dict = dict(zip(objsize_list, data))
    for k, v in dict(data_dict).items():
        if v is None or v is 'NA':
            del data_dict[k]

    return [list(data_dict.keys()), list(data_dict.values())]


def get_buildwise_data(version, object_size, bench, configs, operation, param, subparam=None):
    data = []
    builds_list = get_chain(version)

    buckets, objects, sessions = get_configs(bench, configs)

    for build in builds_list:
        data_routine(data, build, object_size, bench,
                     operation, param, buckets, objects, sessions, subparam)

    data_dict = dict(zip(builds_list, data))
    for k, v in dict(data_dict).items():
        if v is None or v is 'NA':
            del data_dict[k]

    return [list(data_dict.keys()), list(data_dict.values())]


def get_data_based_on_filter(Xfilter, version, option, bench, configs, operation, param, subparam=None):
    if Xfilter == 'build':
        return get_objsizewise_data(option, bench, configs, operation, param, subparam)
    else:
        return get_buildwise_data(version, option, bench, configs, operation, param, subparam)
