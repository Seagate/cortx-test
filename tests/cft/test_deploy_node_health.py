import json
import logging

import pytest

from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.constants import Sizes
from libs.csm.cli.cortx_node_cli_resource import CortxNodeCLIResourceOps
from libs.s3 import CM_CFG


class NodeHealth:
    @classmethod
    def setup_class(cls):
        cls.log.info("STARTED : Setup operations at test suit level")
        cls.log = logging.getLogger(__name__)
        cls.host_ip = CM_CFG["nodes"][0]["host"]
        cls.username = "nodeadmin"
        cls.password = "seagate"  # ToDo read nodeadmin password from yaml
        cls.log.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        self.log.info("STARTED : Setup operations at test function level")
        self.resource_cli = CortxNodeCLIResourceOps()
        self.resource_cli.open_connection()
        # SSH to host using factory admin user
        self.node_obj = Node(hostname=self.host_ip, username=self.username, password=self.password)
        self.log.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        self.log.info("STARTED : Teardown operations at test function level")
        self.resource_cli.logout_node_cli()
        self.node_obj.disconnect()
        self.log.info("ENDED : Teardown operations at test function level")

    def teardown_class(self):
        pass

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22520")
    def test_22520(self):
        """Verify resource discover command"""
        # Enter cortx_setup resource discover command
        resp = self.resource_cli.resource_discover_node_cli(timeout=5 * 60)
        assert_utils.assert_true(resp[0], resp[1])
        #   expect Command should complete within 5 minutes
        # Verify json file created in predefined location
        file_path = ""  # ToDo
        resp = self.node_obj.get_file_size(file_path)
        assert_utils.assert_true(resp[1] < 4 * Sizes.MB, "The file size more than 4MB")
        #   expect File has less than 4 MB size
        # Verify json format and contents of the file
        read_resp = self.node_obj.read_file(file_path)
        self.log.info("======================================================")
        self.log.info(read_resp)
        self.log.info("======================================================")
        _ = json.load(read_resp)
        #   expect Resource map should be present in the file # ToDo

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22526")
    def test_22526(self):
        """Verify resource show --health command"""
        # Enter cortx_setup resource show --health command
        resp = self.resource_cli.resource_health_show_node_cli(timeout=5 * 60)
        assert_utils.assert_true(resp[0], resp[1])
        #   expect Command should complete within 5 minutes
        # Verify json file created in predefined location
        file_path = ""  # ToDo
        resp = self.node_obj.get_file_size(file_path)
        assert_utils.assert_true(resp[1] < 4 * Sizes.MB, "The file size more than 4MB")
        #   expect File has less than 4 MB size
        # Verify json format and contents of the file
        read_resp = self.node_obj.read_file(file_path)
        self.log.info("======================================================")
        self.log.info(read_resp)
        self.log.info("======================================================")
        _ = json.load(read_resp)
        #   expect Resource map should be present in the file # ToDo

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22527")
    def test_22527(self):
        """Verify resource show --health command with resource path"""
        rpath = "rpath"  # ToDo
        # Enter cortx_setup resource show --health command rpath
        resp = self.resource_cli.resource_health_show_rpath_node_cli(timeout=5 * 60, rpath=rpath)
        assert_utils.assert_true(resp[0], resp[1])
        #   expect Command should complete within 5 minutes
        # Verify json file created in predefined location
        file_path = ""  # ToDo
        resp = self.node_obj.get_file_size(file_path)
        assert_utils.assert_true(resp[1] < 4 * Sizes.MB, "The file size more than 4MB")
        #   expect File has less than 4 MB size
        # Verify json format and contents of the file
        read_resp = self.node_obj.read_file(file_path)
        self.log.info("======================================================")
        self.log.info(read_resp)
        self.log.info("======================================================")
        _ = json.load(read_resp)
        #   expect Resource map should be present in the file # ToDo

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22528")
    def test_22528(self):
        """Verify resource show --health with removing a drive from 5U84"""
        # ToDo: Physically remove drive (Manual test) (HW only)

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22529")
    def test_22529(self):
        """Verify resource show --health with removing a PSU from server node"""
        # ToDo: Physically remove PSU for a given node (Manual test) (HW only)

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-22530")
    def test_22530(self):
        """Verify resource show --health with wrong rpath"""
        rpath = "wrong rpath"  # ToDo
        # Enter cortx_setup resource show --health command with wrong parameters
        resp = self.resource_cli.resource_health_show_rpath_node_cli(5 * 60, rpath)
        error_msg = "Wrong rpath"  # ToDo
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.log.info(
            "Requesting resource health failed with wrong rpath with error %s",
            resp[1])
