import sys
import pytest
import logging
from libs.csm.rest.csm_rest_capacity import SystemCapacity
from libs.common.hctl_commands import Hctl_util

class TestSystemCapacity():
    """System Capacity Testsuite"""
    @classmethod
    def setup_class(self):
        """ This is method is for test suite set-up """
        self.log = logging.getLogger(__name__)
        self.log.info("Initializing test setups ......")
        self.system_capacity = SystemCapacity()
        self.log.info("Initiating Rest Client ...")
        self.hctl_obj = Hctl_util()

    def tearDown(self):
        pass

    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-")
    def test_4202(self):
        """Test REST API for GET request with default arguments return 200 and json response
        :avocado: tags=capacity_usage
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        csm_total, csm_avail, csm_used, csm_used_percent, csm_unit = self.system_capacity.parse_capacity_usage()
        ha_total,ha_avail,ha_used = self.hctl_obj.get_sys_capacity()
        ha_used_percent = round((ha_used / ha_total) * 100, 1)
        csm_used_percent = round(csm_used_percent, 1)
        self.assertEqual(csm_total,ha_total,"Total capacity check failed.")
        self.assertEqual(csm_avail,ha_avail,"Available capacity check failed.")
        self.assertEqual(csm_used,ha_used,"Used capacity check failed.")
        self.assertEqual(csm_used_percent, ha_used_percent,"Used capacity percentage check failed.")
        self.assertEqual(csm_unit,'BYTES',"Capacity unit check failed.")
        self.log.info("Capacity reported by CSM matched HCTL response.")
        self.log.info("##### Test ended -  {} #####".format(test_case_name))
