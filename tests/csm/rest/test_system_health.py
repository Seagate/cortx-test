import sys
import pytest
import logging
from libs.csm.rest.csm_rest_system_health import SystemHealth

class TestSystemHealth():
    """System Health Testsuite"""

    @classmethod
    def setup_class(self):
        """ This is method is for test suite set-up """
        self.log = logging.getLogger(__name__)
        self.log.info("Initializing test setups ......")
        self.system_health = SystemHealth()
        self.log.info("Initiating Rest Client for Alert ...")

    def tearDown(self):
        pass

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-12786')
    def test_6813(self):
        """Test that GET request for API '/api/v1/system/health/summary ' 
        returns 200 response with overall health status of the system.
        :avocado: tags=system_health
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        expected_response = self.system_health.success_response
        result = self.system_health.verify_health_summary(expected_response)
        assert result
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-17867')
    def test_6819(self):
        """
        Test that GET request for API '/api/v1/system/health/node?node_id=<node_id>' 
        for node health summary returns 200 response with overall health summary 
        for the specific node or enclosure
        :avocado: tags=system_health
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        for node in ["storage", "node-1", "node-2"]:
            expected_response = self.system_health.success_response
            result = self.system_health.verify_health_node(
                expected_response, node=node)
            assert result
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.skip(reason="Known issue EOS-15448 ")
    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-17868')
    def test_6820(self):
        """
        Test that GET request for API '/api/v1/system/health/node?' 
        for node health summary returns 200 response with overall health summary 
        for entire system in case user does not provide specific node or enclosure id.
        :avocado: tags=system_health
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        expected_response = self.system_health.success_response
        result = self.system_health.verify_health_node(
            expected_response, node="")
        assert result
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.skip(reason="Known issue EOS-15448 ")
    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-17869')
    def test_6826(self):
        """
        Test that GET request for API '/api/v1/system/health/view?node_id=<node_id>' 
        for node health view returns 200 response with overall health summary 
        and list of alerts for that specific node or enclosure
        :avocado: tags=system_health
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        for node in ["storage", "node-1", "node-2"]:
            expected_response = self.system_health.success_response
            result = self.system_health.verify_health_view(
                expected_response, node=node)
            assert result
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-17870')
    def test_6827(self):
        """
        Test that GET request for API '/api/v1/system/health/view?' for node health view 
        returns 200 response with overall health summary and list of alerts 
        for entire system in case user does not provide specific node or enclosure id.
        :avocado: tags=system_health
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        expected_response = self.system_health.success_response
        result = self.system_health.verify_health_view(
            expected_response, node="")
        assert result
        self.log.info("##### Test ended -  {} #####".format(test_case_name))
