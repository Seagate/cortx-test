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
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest module to test Node helper methods."""

import logging
import pytest

from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from config import CMN_CFG


def get_node_obj_list():
    """Get all node object list."""
    node_obj_list = []
    nodes = CMN_CFG.get("nodes")
    for node, _ in enumerate(nodes):
        host = nodes[node]["hostname"]
        uname = nodes[node]["username"]
        passwd = nodes[node]["password"]
        node_obj_list.append(Node(hostname=host,
                                  username=uname,
                                  password=passwd))

    return node_obj_list


class TestNodeHelper:
    """Test node helper class."""

    def setup(self):
        """Test node helper constructor."""
        self.log = logging.getLogger(__name__)

    @pytest.mark.parametrize("nobj", get_node_obj_list())
    def test_get_ldap_credential(self, nobj):
        """Test the get ldap credential method."""
        nobj.connect()
        self.log.info(nobj)
        resp = nobj.get_ldap_credential()
        self.log.info(resp)
        assert_utils.assert_is_not_none(resp[0], f"Failed to generate LDAP USER: {resp[0]}")
        assert_utils.assert_is_not_none(resp[1], f"Failed to generate LDAP PASS: {resp[1]}")
        nobj.disconnect()
