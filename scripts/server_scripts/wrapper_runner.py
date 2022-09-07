#!/usr/bin/python3
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
""" Wrapper to run the EMAP list and corrupt """

import os
import sys

import argparse
import metadata_parser

parser = argparse.ArgumentParser(description="Basic Arguments to run the script")
parser.add_argument('-m', action='store', dest='mfile', help='Metadata Path')

parser.add_argument('-corrupt_emap', action='store', dest='corrupt_emap',
                    help='Induce Error in Emap specified by Cob Id'
                         ' (can be retrieved from list_emap command)')
parser.add_argument('-list_emap', action='store_true', default=False, dest='list_emap',
                    help='Display all Emap keys with device id'
                         'e.g. wrapper_runner.py '
                         '-list_emap -m '
                         '/var/motr/m0d-0x7200000000000001:0xc/db/o/100000000000000:2a '
                         '-parse_size 10485760')
parser.add_argument('-parse_size', action='store', dest='parse_size', type=int,
                    help='Limit for metadata parsing size in bytes for list_emap and verify option')
parser.add_argument('-offset', action='store', default=0, type=int, dest='seek_offset',
                    help='Starting offset of metadata file in multiple of 8 bytes')


args = parser.parse_args()
filename = args.mfile
oid = args.corrupt_emap
parse_size = args.parse_size
offset = args.seek_offset

md = metadata_parser.MetadataParser(filename, parse_size)
if not os.walk(filename):
    print('Failed: The path specified does not exist or Missing file path')
    sys.exit(1)
md.read_metadata_file()

if args.list_emap:
    md.ListAllEmapPerDevice()
elif args.corrupt_emap:
    md.CorruptEmap(oid)
