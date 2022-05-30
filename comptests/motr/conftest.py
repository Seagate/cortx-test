# -*- coding: utf-8 -*-
# !/usr/bin/python
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
"""This file contains motr Pytest fixtures"""

import pytest
from libs.motr import FILE_BLOCK_COUNT
from libs.motr.layouts import BSIZE_LAYOUT_MAP
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

@pytest.fixture(name="motr", scope="module")
def motr_lib_object():
    """
    To initiate the motr core lib instance
    """
    obj = MotrCoreK8s()
    yield obj
    del obj


@pytest.fixture(scope="function")
def run_m0_io(motr):
    """
    This will run the motr IO using m0cp, m0cat, m0unlink utilities and returns the dict of objects
    """
    object_dict = {}
    cortx_node = None
    def _run_m0_io(node, bsize_layout_map=BSIZE_LAYOUT_MAP, block_count=FILE_BLOCK_COUNT,
                    run_m0cat=True, delete_objs=True):
        nonlocal object_dict, cortx_node
        obj_dict = motr.run_motr_io(node, bsize_layout_map, block_count, run_m0cat, delete_objs)
        object_dict = obj_dict
        cortx_node = node
        return obj_dict
    yield _run_m0_io
    for obj in object_dict:
        if not object_dict[obj]['deleted']:
            motr.unlink_cmd(obj, object_dict[obj]['block_size'], cortx_node)
