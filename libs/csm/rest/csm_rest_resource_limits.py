#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Test library for CSM load testing and resource limits validation."""
import concurrent.futures
from http import HTTPStatus

import commons.errorcodes as err
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class RestResourceLimits(RestTestLib):
    """REST client for testing CSM resource limits."""

    @RestTestLib.authenticate_and_login
    def flood(self, endpoint, num_iters):
        """
        Send the provided number of requests to the provided endpoint.

        :param endpoint: API endpoint to flood to.
        :param num_iters: number of requests to be sent.
        :returns: True if requests limit was reached, False otherwise.
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for _ in range(num_iters):
                future = executor.submit(
                    self.restapi.rest_call,
                    request_type="get", endpoint=endpoint, headers=self.headers)
                futures.append(future)
            for future in concurrent.futures.as_completed(futures):
                try:
                    resp = future.result()
                    if resp.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                        return True
                except BaseException as any_error:
                    raise CTException(
                        err.CSM_REST_GET_REQUEST_FAILED,
                        "Unhandled exception during flooding") from any_error
        return False
