# !/usr/bin/python
# -*- coding: utf-8 -*-
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
"""
Python file to maintain all constant msg, error, commands for data integrity tests
"""
#DI feature control flags
s3_range_read_flag = "S3_RANGED_READ_ENABLED"  # enable ranged reads
s3_md5_check_flag = "S3_READ_MD5_CHECK_ENABLED"  # enable data integrity checksum check on S3 GET
s3_disable_data_corr_iem = "S3_DI_DISABLE_DATA_CORRUPTION_IEM"  # disable IEM in case of data integrity checksum fails
s3_disable_metadata_corr_iem = "S3_DI_DISABLE_METADATA_CORRUPTION_IEM"  # disable IEM in case if metadata corruption is detected

#DI fault injection flags
#ref : https://github.com/Seagate/cortx-s3server/blob/cortx-1.0/docs/object-protection-testing.md
di_data_corrupted_on_write = "di_data_corrupted_on_write"
di_data_corrupted_on_read = "di_data_corrupted_on_read"
di_obj_md5_corrupted = "di_obj_md5_corrupted"
di_metadata_bcktname_on_write_corrupted = "di_metadata_bcktname_on_write_corrupted"
di_metadata_objname_on_write_corrupted = "di_metadata_objname_on_write_corrupted"
di_metadata_bcktname_on_read_corrupted = "di_metadata_bcktname_on_read_corrupted"
di_metadata_objname_on_read_corrupted = "di_metadata_objname_on_read_corrupted"
object_metadata_corrupted = "object_metadata_corrupted"
di_metadata_bucket_or_object_corrupted = "di_metadata_bucket_or_object_corrupted"
part_metadata_corrupted = "part_metadata_corrupted"
di_part_metadata_bcktname_on_write_corrupted = "di_part_metadata_bcktname_on_write_corrupted"
di_part_metadata_objname_on_write_corrupted = "di_part_metadata_objname_on_write_corrupted"
di_part_metadata_bcktname_on_read_corrupted = "di_part_metadata_bcktname_on_read_corrupted"
di_part_metadata_objname_on_read_corrupted = "di_part_metadata_objname_on_read_corrupted"
