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
"""
Schemas to be used in backend of the dashboard
"""


def get_common_schema(data):
    entry = {
        'Branch': data['branch'],
        'Count_of_Servers': data['nodes'],
        'Percentage_full': data['pfull'],
        'Iteration': data['itrns'],
        'Custom': data['custom'],
        'Buckets': data['buckets'],
        'Sessions': data['sessions']
    }
    return entry


def get_statistics_schema(data):
    entry = get_common_schema(data)
    entry['Build'] = data['build']

    return entry


def get_complete_schema(data):
    entry = get_common_schema(data)
    entry['Build'] = data['build']
    entry['Object_Size'] = data['objsize']
    entry['Operation'] = data['operation']
    entry['Name'] = data['name']
    # entry['Count_of_Clients'] = data['clients'],

    return entry


statistics_column_headings = [
    'Objects', 'Write Throughput (MBps)', 'Write IOPS', 'Write Latency (ms)', 'Write TTFB (ms)',
    'Read Throughput (MBps)', 'Read IOPS', 'Read Latency (ms)', 'Read TTFB (ms)']

multiple_buckets_headings = [
    'Objects', 'Write Throughput (MBps)', 'Write IOPS', 'Write Latency (ms)',
    'Read Throughput (MBps)', 'Read IOPS', 'Read Latency (ms)']

bucketops_headings = [
    'Create Buckets (BINIT)', 'Put Objects (PUT)', 'Listing Objects (LIST)', 'Get Objects (GET)',
    'Delete Objects (DEL)', 'Clear Buckets (BCLR)', 'Delete Buckets (BDEL)']


def get_dropdown_labels(dropdown_type):
    mapping = {
        'nodes': ' Nodes',
        'pfill': '% Fill',
        'itrns': ' Iteration',
        'buckets': ' Bucket(s)',
        'sessions': ' Session(s)'
    }

    return mapping[dropdown_type]


def get_bucketops_modes():
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
