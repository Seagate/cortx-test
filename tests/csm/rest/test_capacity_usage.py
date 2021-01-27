import sys
import pytest
import logging
from libs.csm.rest.csm_rest_capacity import SystemCapacity
from commons.helpers.health_helper import Health
from commons.utils import assert_utils
from commons.utils import config_utils

class TestSystemCapacity():
    """System Capacity Testsuite"""
    @classmethod
    def setup_class(self):
        """ This is method is for test suite set-up """
        self.log = logging.getLogger(__name__)
        self.log.info("Initializing test setups ......")
        self.system_capacity = SystemCapacity()
        self.log.info("Initiating Rest Client ...")
        main_conf = config_utils.read_yaml("config\common_config.yaml")[1]
        self.health_helper = Health(main_conf["server_hostname"]+main_conf["host_domain"],
                                    main_conf["server_username"],
                                    main_conf["server_password"])

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-15200')
    def test_4202(self):
        """Test REST API for GET request with default arguments return 200 and json response
        :avocado: tags=capacity_usage
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        csm_total, csm_avail, csm_used, csm_used_percent, csm_unit = self.system_capacity.parse_capacity_usage()
        ha_total,ha_avail,ha_used = self.health_helper.get_sys_capacity()
        ha_used_percent = round((ha_used / ha_total) * 100, 1)
        csm_used_percent = round(csm_used_percent, 1)
        assert_utils.assert_equals(csm_total,ha_total,"Total capacity check failed.")
        assert_utils.assert_equals(csm_avail,ha_avail,"Available capacity check failed.")
        assert_utils.assert_equals(csm_used,ha_used,"Used capacity check failed.")
        assert_utils.assert_equals(csm_used_percent, ha_used_percent,"Used capacity percentage check failed.")
        assert_utils.assert_equals(csm_unit,'BYTES',"Capacity unit check failed.")
        self.log.info("Capacity reported by CSM matched HCTL response.")
        self.log.info("##### Test ended -  {} #####".format(test_case_name))
