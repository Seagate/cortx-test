#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest module to test Node helper methods."""

import pytest

from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from config import CMN_CFG


def get_node_obj_list():
    """Get all node object list."""
    node_obj_list = []
    for node in range(len(CMN_CFG["nodes"])):
        host = CMN_CFG["nodes"][node]["hostname"]
        uname = CMN_CFG["nodes"][node]["username"]
        passwd = CMN_CFG["nodes"][node]["password"]
        node_obj_list.append(Node(hostname=host,
                                  username=uname,
                                  password=passwd))

    return node_obj_list


class TestNodeHelper:
    """Test node helper class."""

    @pytest.mark.parametrize("nobj", get_node_obj_list())
    def test_get_ldap_credential(self, nobj):
        """Test the get ldap credential method."""
        nobj.connect()
        resp = nobj.get_ldap_credential()
        assert_utils.assert_is_not_none(resp[0], f"Failed to generate LDAP USER: {resp[0]}")
        assert_utils.assert_is_not_none(resp[1], f"Failed to generate LDAP PASS: {resp[1]}")
        nobj.disconnect()
