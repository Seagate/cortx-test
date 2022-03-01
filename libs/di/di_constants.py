# !/usr/bin/python
# -*- coding: utf-8 -*-
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
