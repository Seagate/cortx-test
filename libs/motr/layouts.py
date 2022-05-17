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

"""
Layout id defines the object unit size which cannot be less than
the page size.
1 - 4KB, 2 - 8KB, 3 - 16KB, 4 - 32KB, 5 - 64KB and so on.
On RHEL aarch64 platform the page size is 64KB, hence the default layout id must be 5.
Ref motr/Layout.h for details.
"""

ARCH = {'CONFIG_X86_64': '1', 'CONFIG_AARCH64': '5'}

bsize_list = ['4K', '8K', '16K', '32K', '64K', '128K', '256K', '512K',
              '1M', '2M', '4M', '8M', '16M', '32M']

layout_ids = ['1', '2', '3', '4', '5', '6', '7', '8',
              '9', '10', '11', '12', '13', '14']

BSIZE_LAYOUT_MAP = {'4K': 1, '8K': 2, '16K': 3, '32K': 4, '64K': 5, '128K': 6, '256K': 7,
                    '512K': 8, '1M': 9, '2M': 10, '4M': 11, '8M': 12, '16M': 13, '32M': 14}

LAYOUT_BSIZE_MAP = {1: '4K', 2: '8K', 3: '16K', 4: '32K', 5: '64K', 6: '128K', 7: '256K',
                    8: '512K', 9: '1M', 10: '2M', 11: '4M', 12: '8M', 13: '16M', 14: '32M'}
