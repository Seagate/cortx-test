"""Performance schemas consumed by backend and essential for database"""
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


def get_common_schema(data):
    """
    function for getting common performance schema wrt database
    and provided data

    Args:
        data: data needed for query

    Returns:
        dict: data dict with db key mapped with given data
    """
    entry = {
        'OS': data['OS'],
        'Branch': data['branch'],
        'Count_of_Servers': data['nodes'],
        'Count_of_Clients': data['clients'],
        'Percentage_full': data['pfull'],
        'Iteration': data['itrns'],
        'Custom': data['custom'],
        'Buckets': data['buckets'],
        'Sessions': data['sessions']
    }
    return entry


def get_statistics_schema(data):
    """
    function for getting stats specific performance schema
    wrt database and provided data

    Args:
        data: data needed for query

    Returns:
        dict: data dict with db key mapped with given data
    """
    entry = get_common_schema(data)
    entry['Build'] = data['build']

    return entry


def get_graphs_schema(data, xfilter, xfilter_tag):
    """
    function for getting graphs specific performance schema
    wrt database and provided data

    Args:
        data: data needed for query

    Returns:
        dict: data dict with db key mapped with given data
    """
    entry = get_common_schema(data)
    entry[xfilter] = data[xfilter_tag]
    entry['Name'] = data['name']

    return entry


def get_multi_concurrency_schema(data, xfilter, xfilter_tag):
    """
    function for getting graphs multi-concurrency specific performance schema
    wrt database and provided data

    Args:
        data: data needed for query

    Returns:
        dict: data dict with db key mapped with given data
    """
    entry = get_common_schema(data)
    del entry['Sessions']
    entry['Object_Size'] = data['objsize']
    entry[xfilter] = data[xfilter_tag]
    entry['Name'] = data['name']

    return entry


def get_complete_schema(data):
    """
    function for getting complete performance schema
    wrt database and provided data

    Args:
        data: data needed for query

    Returns:
        dict: data dict with db key mapped with given data
    """
    entry = get_common_schema(data)
    entry['Build'] = data['build']
    entry['Object_Size'] = data['objsize']
    entry['Operation'] = data['operation']
    entry['Name'] = data['name']
    entry['Cluster_State'] = {"$exists": False}
    entry['Additional_op'] = {"$exists": False}

    return entry


def get_degraded_schema(data):
    """
    function for getting complete performance schema
    wrt database and provided data for degraded cluster
    Args:
        data: data needed for query
    Returns:
        dict: data dict with db key mapped with given data
    """
    entry = get_common_schema(data)
    entry['Build'] = data['build']
    entry['Object_Size'] = data['objsize']
    entry['Operation'] = data['operation']
    entry['Name'] = data['name']
    entry['Cluster_State'] = data['cluster_state']

    return entry


def get_copyobject_schema(data):
    """
    function for getting complete performance schema
    wrt database and provided data for copy object

    Args:
        data: data needed for query

    Returns:
        dict: data dict with db key mapped with given data
    """
    entry = get_common_schema(data)
    entry['Build'] = data['build']
    entry['Object_Size'] = data['objsize']
    entry['Operation'] = data['operation']
    entry['Name'] = data['name']
    entry['Cluster_State'] = {"$exists": False}
    entry['Additional_op'] = 'Copy_op'

    return entry


statistics_column_headings = [
    'Samples', 'Read Throughput (MBps)', 'Read IOPS', 'Read Latency (ms)', 'Read TTFB Avg (ms)',
    'Read TTFB 99% (ms)', 'Write Throughput (MBps)', 'Write IOPS', 'Write Latency (ms)']

multiple_buckets_headings = [
    'Samples', 'Read Throughput (MBps)', 'Read IOPS', 'Read Latency (ms)',
    'Write Throughput (MBps)', 'Write IOPS', 'Write Latency (ms)']

bucketops_headings = [
    'Create Buckets (BINIT)', 'Put Objects (PUT)', 'Listing Objects (LIST)', 'Get Objects (GET)',
    'Delete Objects (DEL)', 'Clear Buckets (BCLR)', 'Delete Buckets (BDEL)']

copyobj_headings = [
    'Samples', 'Read Throughput (MBps)', 'Read IOPS', 'Read Latency (ms)', 'Read TTFB Avg (ms)',
    'Read TTFB 99% (ms)', 'Copy Object Throughput (MBps)', 'Copy Object IOPS',
    'Copy Object Latency (ms)', 'Write Throughput (MBps)', 'Write IOPS', 'Write Latency (ms)']

def get_dropdown_labels(dropdown_type):
    """
    function for getting label extensions wrt dropdown options

    Args:
        data: variable with dropdown name

    Returns:
        string: corresponding mapping for the input string
    """
    mapping = {
        'branch': ' Branch',
        'build': ' Build',
        'nodes': ' Nodes',
        'clients': ' Clients',
        'pfill': '% Fill',
        'itrns': ' Iteration',
        'buckets': ' Bucket(s)',
        'sessions': ' Concurrency'
    }

    return mapping[dropdown_type]


def get_bucketops_modes():
    """
    function to get bucketops mode mapping

    Returns:
        dict: dict of all bucketops modes
    """
    modes = {
        '2': 'BINIT',
        '3': 'PUT',
        '4': 'LIST',
        '5': 'GET',
        '6': 'DEL',
        '7': 'BCLR',
        '8': 'BDEL'
    }

    return modes
