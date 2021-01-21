"""Test library for capacity related operations.
   Author: Divya Kachhwaha
"""
import time
import json
#from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from ctp.utils import ctpyaml


class SystemCapacity(RestTestLib):
    """RestCsmUser contains all the Rest API calls for system health related operations"""

    def __init__(self):
        """
        Initialize the rest api
        """
        super(SystemCapacity, self).__init__()

    @RestTestLib.authenticate_and_login
    def get_capacity_usage(self):
        """Get the system capacity usage

        :return [obj]: Json response
        """
        try:
            # Building request url
            self._log.info("Reading System Capacity...")
            endpoint = self.config["capacity_endpoint"]
            self._log.info(
                "Endpoint for reading capacity is {}".format(endpoint))

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self._log.info(
                "CSM REST response returned is:\n {}".format(response.json()))
            return response

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                SystemCapacity.get_capacity_usage.__name__,
                error))
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def parse_capacity_usage(self, expected_response=const.SUCCESS_STATUS):
        """Parse the Json response to extract used, available and total capacity

        :param expected_response: expected status code
        :return [tuple]: tuple of total_cap, avail_cap, used_cap, used_percent, cap_unit
        """
        response = self.get_capacity_usage()
        if response.status_code == expected_response:
            self._log.info("Expected response check Passed.")
        else:
            self._log.error("Expected response check Failed.")
            return False

        response_json = response.json()
        total_cap = response_json['size']
        avail_cap = response_json['avail']
        used_cap = response_json['used']
        used_percent = response_json['usage_percentage']
        cap_unit = response_json['unit']
        return total_cap, avail_cap, used_cap, used_percent, cap_unit
