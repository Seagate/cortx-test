#Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
"""Test library for Information related operations."""
import json

from libs.csm.rest.csm_rest_test_lib import RestTestLib

class RestInformation(RestTestLib):
    """RestInformation contains all the Rest API calls for information related operations"""

    def __init__(self):
        super(RestInformation, self).__init__()
        self.iam_user = None
    
    def get_valid_compatible_payload(self):
        payload = {}
        required = ["CORTX >= 2.0.0-0"]
        payload.update({"requires": required})
        return payload

    def get_valid_incompatible_payload(self):
        payload = {}
        required = ["CORTX >= 3.0.0-0"]
        payload.update({"requires": required})
        return payload

    def get_invalid_rules_payload(self):
        payload = {}
        required = ["Invalid rule"]
        payload.update({"requires": required})
        return payload

    def get_invalid_request_body_payload(self):
        payload = {}
        payload.update({"random_key": "random_val"})
        return payload

    payload_types = {
        "compatible" : get_valid_compatible_payload,
        "incompatible" : get_valid_incompatible_payload,
        "invalid_rules": get_invalid_rules_payload,
        "invalid_request_body": get_invalid_request_body_payload,
    }

    def get_version_compatibility_payload(self, payload_type="compatible"):
        self.log.info("Getting payload of type : %s", payload_type)
        return self.payload_types[payload_type](self)

    def verify_version_compatibility(self, resource, resource_id, payload):
        # get the endpoint
        base_endpoint = self.config["version_endpoint"]
        endpoint = f"{base_endpoint}/{resource}/{resource_id}"
        self.log.debug("Endpoint for iam user is %s", endpoint)

        response = self.restapi.rest_call(request_type="post",
                                            endpoint=endpoint,
                                            data=json.dumps(payload), headers=self.headers)
        self.log.debug("response is : %s", response)
        return response


