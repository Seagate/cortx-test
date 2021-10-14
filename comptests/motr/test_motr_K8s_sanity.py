import pytest
import logging
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

LOGGER = logging.getLogger(__name__)


class TestExecuteK8Sanity:
    """Execute Motr K8s Test suite"""

    @pytest.yield_fixture(autouse=True)
    def setup_class(self):
        """ Setup class for running Motr tests"""
        LOGGER.info("STARTED: Setup Operation")
        self.motr_obj = MotrCoreK8s()
        LOGGER.info("ENDED: Setup Operation")
        yield
        # Perform the clean up for each test.
        LOGGER.info("STARTED: Teardown Operation")
        del self.motr_obj
        LOGGER.info("ENDED: Teardown Operation")

    def test_motr_k8s_lib(self):
        # TODO: This a sample test for the usage, need to delete it later
        print(self.motr_obj.cluster_info)
        print(self.motr_obj.profile_fid)
        print(self.motr_obj.node_dict)    
        print(self.motr_obj.storage_nodes)
        print(self.motr_obj.get_primary_podNode())
        print(self.motr_obj.get_podNode_endpoints())