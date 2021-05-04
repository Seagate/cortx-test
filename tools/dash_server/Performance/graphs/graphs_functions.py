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
import re

from Performance.global_functions import get_db_details, get_distinct_keys
from Performance.mongodb_api import count_documents, find_documents

meta_data_objs = ['1Kb']


def get_metrics(bench):
    if bench == 'S3bench':
        return ['Throughput', 'Latency', 'IOPS', 'TTFB']
    else:
        return ['Throughput', 'Latency', 'IOPS']


def get_yaxis_heading(metric):
    if metric == "Throughput":
        return "{} (MBps)".format(metric)
    elif metric == "IOPS":
        return "{}".format(metric)
    else:
        return "{} (ms)".format(metric)


def get_structure_trace(Scatter, operation, metrics, option, x_axis, y_data):
    trace = Scatter(
        name='{} {} - {}'.format(operation, metrics, option),
        x=x_axis,
        y=y_data,
        hovertemplate='<br>%{y}<br>' + '<b>{} - {}</b><extra></extra>'.format(
            operation, option),
    )
    return trace


def get_operations(bench, operation_opt):
    if bench == 'S3bench':
        if operation_opt == 'both':
            return ['Read', 'Write']
        else:
            return [operation_opt.capitalize()]
    else:
        if operation_opt == 'both':
            return ['read', 'write']
        else:
            return [operation_opt]


def return_compliment(xfilter):
    if xfilter == 'Build':
        return 'Object_Size'
    else:
        return 'Build'


def get_xaxis(xfilter, release, branch, option, bench):
    # Version_Branch_Build_Iteration_NodeCount_ClientCount_PercentFull_Benchmark_ObjSize_NoOfBuckets_Operation_Sessions
    if xfilter == 'Object_Size':
        pkeys = get_distinct_keys(release, 'PKey', {
            'Branch': branch, xfilter: option, 'Name': bench
        })
        profiles = []
        for key in pkeys:
            profile = "_".join(key.split("_")[2:8])
            if profile not in profiles:
                profiles.append(profile)

        return profiles
    else:
        obj_sizes = get_distinct_keys(release, 'Object_Size', {
            'Branch': branch, xfilter: option, 'Name': bench
        })
        for obj in meta_data_objs:
            if obj in obj_sizes:
                obj_sizes.remove(obj)
        return obj_sizes


def sort_objectsizes(data_dict):
    sizes_sorted = {
        'KB': {}, 'MB': {}, 'GB': {},
    }
    rest = {}
    data_sorted = {}
    for size, data in data_dict.items():
        if size.lower().endswith("kb"):
            sizes_sorted['KB'][size] = data
        elif size.lower().endswith("mb"):
            sizes_sorted['MB'][size] = data
        elif size.lower().endswith("gb"):
            sizes_sorted['GB'][size] = data
        else:
            rest[size] = data

    for size_unit in sizes_sorted.keys():
        objects = list(sizes_sorted[size_unit].keys())
        temp = [int(obj[:-2]) for obj in objects]
        temp.sort()
        for item in temp:
            for obj in objects:
                if obj[:-2] == str(item):
                    data_sorted[str(item) +
                                size_unit] = sizes_sorted[size_unit][obj]
                    break

    data_sorted.update(rest)
    return data_sorted

def get_placeholder(components):
    placeholder = ", ".join(
        [components[0], components[2][:-1]+' nodes'])
    if components[4][:-2] != '0':
        placeholder = placeholder + ", " + components[4][:-2] + '% fill'
    if components[-1] != 'NA':
        placeholder = placeholder + ", " + components[-1]
    if components[1] != 'ITR1':
        placeholder = placeholder + ", " + components[1][3:]
    
    return placeholder

def sort_builds(data_dict):
    builds = list(data_dict.keys())

    data_sorted = {}
    for key in builds:
        splits = re.split("_|-", key)

        try:
            int(splits[0])
        except ValueError:
            data_sorted[get_placeholder(key.split("_"))] = data_dict[key]
            del data_dict[key]

    builds = list(data_dict.keys())
    builds.sort(key=lambda x: int(re.split("_|-", x)[0]))
    for build in builds:
        data_sorted[get_placeholder(build.split("_"))] = data_dict[build]

    return data_sorted


def remove_nones(data_dict):
    for k, v in dict(data_dict).items():
        if v is None or v is 'NA':
            del data_dict[k]

    return data_dict


def get_data_for_graphs(xfilter, release, branch, option, profile, bench, configs, operation, metric, param):
    compliment = return_compliment(xfilter)
    uri, db_name, db_collection = get_db_details(release)
    xaxis_list = get_xaxis(xfilter, release, branch, option, bench)
    yaxis_list = []

    config_splits = configs.split('_')
    buckets = int(config_splits[0])
    sessions = int(config_splits[1])

    for item in xaxis_list:
        if xfilter == 'Build':
            PKey = "_".join([str(release), branch[0].upper(), option, profile, bench[:3].upper(),
                             item, str(buckets), operation[0].upper(), str(sessions)])
        else:
            PKey = "_".join([str(release), branch[0].upper(), item, bench[:3].upper(),
                             option, str(buckets), operation[0].upper(), str(sessions)])
        query = {'PKey': PKey}

        try:
            count = count_documents(query=query, uri=uri, db_name=db_name,
                                    collection=db_collection)
            db_data = find_documents(query=query, uri=uri, db_name=db_name,
                                     collection=db_collection)
            try:
                number_of_nodes = db_data[0]['Count_of_Servers']
            except KeyError:
                number_of_nodes = 2
            except IndexError:
                number_of_nodes = 2

            if count > 0:
                try:
                    if param:
                        yaxis_list.append(
                            db_data[0][metric][param] * 1000/number_of_nodes)
                    else:
                        yaxis_list.append(db_data[0][metric]/number_of_nodes)
                except IndexError:
                    yaxis_list.append('NA')
            else:
                yaxis_list.append('NA')
        except KeyError:
            yaxis_list.append(None)
        except IndexError:
            yaxis_list.append(None)

    data_dict = dict(zip(xaxis_list, yaxis_list))

    # remove_nones(data_dict)
    if xfilter == 'Build':
        data_dict = sort_objectsizes(data_dict)
    else:
        data_dict = sort_builds(data_dict)

    return [list(data_dict.keys()), list(data_dict.values())]
