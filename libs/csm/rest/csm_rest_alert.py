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
"""Test library for System Health related operations.
   Author: Divya Kachhwaha
"""
import ast
import time
import json
import datetime
from commons.constants import Rest as const
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib
from commons import errorcodes as err
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class SystemAlerts(RestTestLib):
    """SystemAlerts contains all the Rest API calls for system health related operations"""

    def __init__(self, node_obj: object = None) -> None:
        """
        Initialize the rest api
        :param: node_obj is required if create_alert and resolve_alert functions are used.
        """
        super(SystemAlerts, self).__init__()
        self.node_obj = node_obj

    # pylint: disable=too-many-arguments
    @RestTestLib.authenticate_and_login
    def get_alerts(self, alert_id=None, acknowledged=None, resolved=None,
                   show_active=None, sortby="created_time", direction="desc",
                   offset=1, limit=10, severity=None):
        """
        Gets Alerts: Accessible to CSM users having monitor and manage permissions
        """
        try:
            # Building request url
            self.log.info("Reading alerts...")
            endpoint = self.config["alerts_endpoint"]
            # Adding parameters
            endpoint = self._add_parameters(
                endpoint, alert_id, acknowledged, resolved, show_active,
                sortby, direction, offset, limit, severity)
            self.log.info("Endpoint for reading alert is %s", endpoint)
            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)

            self.log.info(
                "response returned is:\n %s", response)

            return response

        except BaseException as error:
            self.log.error("%s %s: %s", const.EXCEPTION_ERROR,
                           SystemAlerts.get_alerts.__name__, error)
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

    # pylint: disable=too-many-arguments
    @RestTestLib.authenticate_and_login
    def edit_alerts(self, alert_id, ack=True, comment="By Script",
                    ack_key="acknowledged", comment_key="comments"):
        """
        TODO: Comment part is not working
        Gets Alerts: Accessible to CSM users having monitor and manage permissions
        """
        try:
            # Building request url
            self.log.info("Reading alerts...")
            endpoint = self.config["alerts_endpoint"]
            # Adding parameters
            endpoint = "{}/{}".format(endpoint, alert_id)
            self.log.info("Endpoint for reading alert is %s", endpoint)
            # Payload
            payload = {ack_key: ack, comment_key: comment}
            # Fetching api response
            response = self.restapi.rest_call(
                "patch", json_dict=payload, endpoint=endpoint, headers=self.headers)

            self.log.info(
                "response returned is:\n %s", response)

            return response

        except BaseException as error:
            self.log.error("%s %s: %s", const.EXCEPTION_ERROR,
                           SystemAlerts.edit_alerts.__name__, error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-branches
    @staticmethod
    def _add_parameters(endpoint, alert_id=None, acknowledged=None, resolved=False,
                        show_active=None, sortby="created_time", dirby="desc", offset=1, limit=10,
                        severity=None):
        """ Add parameter to endpoint
        """
        if alert_id is not None:
            endpoint = "{}/{}".format(endpoint, alert_id)

        params = []
        if acknowledged is not None:
            params.append("acknowledged={}".format(str(acknowledged).lower()))
        if resolved is not None:
            params.append("resolved={}".format(str(resolved).lower()))
        if show_active is not None:
            params.append("show_active={}".format(str(show_active).lower()))
        if sortby is not None:
            params.append("sortby={}".format(sortby))
        if dirby is not None:
            params.append("dir={}".format(dirby))
        if offset is not None:
            params.append("offset={}".format(offset))
        if limit is not None:
            params.append("limit={}".format(limit))
        if severity is not None:
            params.append("severity={}".format(severity))
        first_ele_flag = False
        for param in params:
            if param is not None:
                if not first_ele_flag:
                    endpoint = "{}?".format(endpoint)
                    first_ele_flag = True
                else:
                    endpoint = "{}&".format(endpoint)
                endpoint = "{}{}".format(endpoint, param)
        return endpoint

    def extract_alert_ids(self, response):
        """Extract and prepare the list of alert id in response.

        :param response: Response of the get alert
        :return [type]: obj
        """
        data = response.json()
        alert_ids = []
        for entry in data["alerts"]:
            alert_ids.append(entry['alert_uuid'])
        self.log.info("Alert IDs detected are : %s", alert_ids)

        return alert_ids

    def ack_all_alerts(self):
        """Acknowledge all the outstanding alerts
        """
        # Read alerts which are not acknowledged
        response = self.get_alerts(acknowledged=False, limit=None)
        if response.json() == []:
            self.log.info("All alerts are acknowledged. No alerts to ack")
        else:
            self.log.debug(response.json())
        # Extract the alert IDs
        alert_ids = self.extract_alert_ids(response)
        # Ack each alert IDs
        for alert_id in alert_ids:
            self.log.info("Acknowledging the alert ID : %s", alert_id)
            self.edit_alerts(alert_id, ack=True)

    def verify_csm_response(self, starttime, alert_type, resolved,
                            *response_checks):
        """Read the CSM alerts from starttime and verify the resolved
        and extended information

        :param starttime: time from which alerts should be considered for
         verification
        :param resolved: expected resolved state
        :return [bool]: True / False based on whether the response matched
        expected results
        """
        starttime = int(starttime)
        self.log.info("Start Time : %s", starttime)
        self.log.info("Extended information to be checked : %s", response_checks)
        self.log.info("CSM: Verifying the new Fault is reported...")
        alert_ids = self.get_alerts_id_after(starttime)
        if alert_ids:
            self.log.info("CSM: New alerts detected are %s", alert_ids)
        else:
            self.log.error("No New Alerts Detected")
            return False

        for alert_id in alert_ids:
            response = self.get_alerts(alert_id)
            if response.status_code == const.SUCCESS_STATUS:
                self.log.info(
                    "Alert ID %s details from Rest API", response)
                resp_flag = True
            else:
                self.log.error("Couldn't read the alert details from Alert ID"
                               "%s", alert_id)
                resp_flag = False

            match_found = True
            if resp_flag:
                alert_info = response.text
                json_response = response.json()
                self.log.info("Response info of the Alert ID %s is ", alert_info)
                if (resolved == json_response['resolved']) and (alert_type in
                                                                alert_info):
                    self.log.info("Alert type check Passed for %s", alert_id)
                    self.log.info("Resolved check Passed for %s", alert_id)
                    for arg in response_checks:
                        if str(arg) in alert_info:
                            self.log.info("Verified %s in the response of "
                                          "alert ID %s", arg, alert_id)
                        else:
                            self.log.error("Couldn't find %s in the response "
                                           "of alert ID %s", arg, alert_id)
                            match_found = False
                            break

                    if match_found:
                        self.log.info("%s", alert_info)
                        self.log.info("Found match for %s", response_checks)
                        return True

        self.log.error("Couldn't find matching alert")
        return False

    def wait_for_alert(self, timeout: int=30, *args, **kwargs):
        """Wait for alert on CSM until timeout is reached.

        :param timeout: in seconds.
        """
        time_lapsed = 0
        resp = False
        while(time_lapsed < timeout and not resp):
            resp = self.verify_csm_response(*args, **kwargs)
            time.sleep(1)
            time_lapsed = time_lapsed + 1
        self.log.info("CSM alert reported within %s seconds.", time_lapsed)
        return resp, "CSM alert is not reported within {}".format(timeout)

    def get_alerts_id_after(self, starttime):
        """
        startime :  start time from which alerts should be considered
        :return [list]: alert ids
        """
        response = self.get_alerts(limit=None)
        data = response.json()
        alert_ids = []
        for entry in data["alerts"]:
            if entry['updated_time'] > starttime:
                alert_ids.append(entry['alert_uuid'])
        if alert_ids == []:
            return False

        starttime = time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime(starttime))
        self.log.info("Alerts generated after %s are : %s", starttime,
                      alert_ids)
        return alert_ids

    @RestTestLib.authenticate_and_login
    def add_comment_to_alerts(self, alert_id, comment_text):
        """
        Function to add comments to Alert
        :param alert_id: id of the alert to add comment to
        :type alert_id: string
        :param comment_text: comment text to add to the alert
        :type comment_text: string
        :return: json response of the add request
        :rtype: json object
        """
        try:
            # Building request url
            self.log.info("Reading alerts...")
            endpoint = self.config["alerts_endpoint"]

            self.log.info("Forming the endpoint...")
            endpoint = "{}/{}/comments".format(endpoint, alert_id)
            self.log.info("Endpoint for reading alert is %s", endpoint)
            payload = {"comment_text": comment_text}

            # Fetching api response
            self.log.info("Fetching the response...")
            self.headers.update(const.CONTENT_TYPE)
            response = self.restapi.rest_call(
                request_type="post", endpoint=endpoint,
                data=json.dumps(payload), headers=self.headers)

            self.log.info(
                "response returned is:\n %s", response)

            return response
        except BaseException as error:
            self.log.error("%s %s: %s", const.EXCEPTION_ERROR,
                           SystemAlerts.add_comment_to_alerts.__name__, error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

    def verify_added_alert_comment(self, user, alert_id, response_alert_comment_added):
        """
        Function to verify the comment added

        :param user: user for which the comment is to be verified
        :type user: string
        :param alert_id: id of the alert to add comment to
        :type alert_id: string
        :param response_alert_comment_added: response of the add comment request
        :type response_alert_comment_added: json object
        :return: boolean result as per the verification <True/False>
        :rtype: bool
        """
        try:
            self.log.info("Getting the alerts")
            response_get = self.get_alerts(login_as=user)

            if response_get.status_code == const.SUCCESS_STATUS:
                alert_id_index_list = \
                    [i for i in range(0, len(response_get.json()["alerts"]))
                     if response_get.json()["alerts"][i]["alert_uuid"] == alert_id]
                alert_id_index = alert_id_index_list[0]

                comment_id_index_list = \
                    [j for j in range(0, len(response_get.json()["alerts"]
                                             [alert_id_index]["comments"]))
                     if response_get.json()["alerts"][alert_id_index]
                     ["comments"][j]["comment_id"] ==
                     response_alert_comment_added["comment_id"]]
                comment_id_index = comment_id_index_list[0]

                self.log.info("Converting utc time to timestamp...")

                created_time = \
                    datetime.datetime.strptime(response_get.json()["alerts"]
                                               [alert_id_index]["comments"]
                                               [comment_id_index]
                                               ["created_time"],
                                               "%Y-%m-%dT%H:%M:%S.%f%z")

                timestamp = datetime.datetime.timestamp(created_time)

                self.log.info("Replacing the utc time in the get response %s "
                              "wih the timestamp %s for comparison",
                              response_get.json()["alerts"][alert_id_index]
                              ["comments"][comment_id_index]["created_time"],
                              int(timestamp))
                resp_obj = response_get.json()
                resp_obj["alerts"][alert_id_index]["comments"][comment_id_index]["created_time"] = \
                    int(timestamp)

                self.log.info("Verifying the comment that was added and that was"
                              " read from GET api")

                if resp_obj["alerts"][alert_id_index]["comments"][comment_id_index] == \
                        response_alert_comment_added:
                    return True
                else:
                    self.log.info("Error: Comment was not added")
                    return False
            else:
                self.log.info(
                    "Get alerts returned non-success response: %s",
                    response_get.status_code)
                return False
        except BaseException as error:
            self.log.error("%s %s: %s", const.EXCEPTION_ERROR,
                           SystemAlerts.verify_added_alert_comment.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

    # pylint: disable-msg=too-many-locals
    def create_alert(self, alert_type, alert_timeout, **kwargs):
        """Create the alert and read get information before and after alert.

        :param alert_type: type of alert to be created.
        :param type: str
        :param alert_timeout: time for which it will wait for alert to be reported on CSM.
        :param type:int
         If alert is not reported within timeout, function will fail.
        :return set: returns false if the it failed at any point,
        else returns set of new alert, before and after alert ids.
        """
        alert_api_obj = GenerateAlertLib()
        expected_status = 200

        self.log.info("Acknowledging existing alerts...")
        self.ack_all_alerts()
        self.log.info("Get alerts...")
        response = self.get_alerts(**kwargs)
        self.log.info("Expected status Code : %s", expected_status)
        self.log.info("Actual status Code : %s", response.status_code)
        if response.status_code != expected_status:
            self.log.error(
                "Failed to Get alert details before alert is generated")
            return False
        before_alert_ids = self.extract_alert_ids(response)
        self.log.info("Before Alert IDs: %s", before_alert_ids)

        response = self.get_alerts(acknowledged=False, resolved=False)
        pre_alerts = self.extract_alert_ids(response)

        self.log.info("Creating alert...")
        # Commented until tested on R2
        #local_path = ras_cons.TELNET_OP_PATH
        #remote_path = ras_cons.REMOTE_TELNET_PATH
        #self.log.info("Copying file %s to %s", local_path, remote_path)
        #self.node_obj.copy_file_to_remote(local_path=local_path,
        #                                  remote_path=remote_path)
        resp = alert_api_obj.generate_alert(
            ast.literal_eval(str('AlertType.%s', alert_type)),
            host_details={'host': self.node_obj.hostname,
                          'host_user': self.node_obj.username,
                          'host_password': self.node_obj.password})
        if not resp[0]:
            self.log.error("Failed to created alert")
            return False

        generared_alert = False
        starttime = time.time()
        timediff = 0
        while timediff < alert_timeout:
            time.sleep(10)
            self.log.info("Reading alerts details...")
            response = self.get_alerts(acknowledged=False, resolved=False)
            post_alerts = self.extract_alert_ids(response)
            new_alerts = list(set(post_alerts) - set(pre_alerts))
            if new_alerts != []:
                generared_alert = True
                break
            timediff = time.time() - starttime
        if generared_alert:
            self.log.info("Successfully created alerts : %s", new_alerts)
            self.log.info("Alert reported on CSM after %s seconds", timediff)
        else:
            self.log.error("Alert is not reported on CSM.")
            return False

        self.log.info("Reading alerts details...")
        response = self.get_alerts(**kwargs)
        self.log.info("Expected status Code : %s", expected_status)
        self.log.info("Actual status Code : %s", response.status_code)
        if response.status_code != expected_status:
            self.log.error(
                "Failed to Get alert details after alert is generated.")
            return False
        after_alert_ids = self.extract_alert_ids(response)
        self.log.info("After alert IDs: %s", after_alert_ids)
        return new_alerts, before_alert_ids, after_alert_ids

    # pylint: disable-msg=too-many-locals
    def resolve_alert(self, resolve_type, alert_timeout, **kwargs):
        """Resolve the alert and return before and after alert IDs

        :param resolve_type: Alert to be resolved
        :param type: str
        :param alert_timeout: timeout for alert to be reported on CSM
        :param type: int
        :return [set]: returns set of new alerts, before resolve alert ids ,
         after resolve alert ids. False if function fails at any check.
        """
        alert_api_obj = GenerateAlertLib()
        expected_status = 200

        self.log.info("Get alerts...")
        response = self.get_alerts(**kwargs)
        self.log.info("Expected status Code : %s", expected_status)
        self.log.info("Actual status Code : %s", response.status_code)
        if response.status_code != expected_status:
            self.log.error(
                "Failed to Get alert details before alert is generated")
            return False
        before_alert_ids = self.extract_alert_ids(response)
        self.log.info("Pre Alert IDs: %s", before_alert_ids)
        # Commented until tested on R2
        #local_path = ras_cons.TELNET_OP_PATH
        #remote_path = ras_cons.REMOTE_TELNET_PATH
        #self.log.info("Copying file %s to %s", local_path, remote_path)
        #self.node_obj.copy_file_to_remote(local_path=local_path,
        #                                  remote_path=remote_path)

        response = self.get_alerts(resolved=False)
        pre_resolve = self.extract_alert_ids(response)

        self.log.info("Resolving alert...")
        resp = alert_api_obj.generate_alert(
            ast.literal_eval(str('AlertType.%s', resolve_type)))
        if not resp[0]:
            self.log.error("Failed to resolve alert")
            return False

        resolved_alert = False
        starttime = time.time()
        timediff = 0
        while timediff < alert_timeout:
            time.sleep(10)
            self.log.info("Reading alerts details...")
            response = self.get_alerts(resolved=False)
            post_resolve = self.extract_alert_ids(response)
            new_alerts = list(set(post_resolve) - set(pre_resolve))
            if new_alerts != []:
                resolved_alert = True
                break
            timediff = time.time() - starttime
        if resolved_alert:
            self.log.info("Successfully resolved alert")
            self.log.info("Alert reported on CSM after %s seconds", timediff)
        else:
            self.log.error("Alert is not reported on CSM.")
            return False

        self.log.info("Reading alerts details...")
        response = self.get_alerts(**kwargs)
        self.log.info("Expected status Code : %s", expected_status)
        self.log.info("Actual status Code : %s", response.status_code)
        if response.status_code != expected_status:
            self.log.error(
                "Failed to Get alert details after alert is generated")
            return False

        after_alert_ids = self.extract_alert_ids(response)
        self.log.info("Post alert IDs: %s", after_alert_ids)
        return before_alert_ids, after_alert_ids

    # pylint: disable=too-many-arguments
    @RestTestLib.authenticate_and_login
    def get_alerts_history(self, sortby="created_time", direction="desc",
                           offset=1, limit=1000, sensor_info=None,
                           start_date=None, end_date=None, duration=None):
        """
        Get alert history: Accessible to CSM users having monitor and manage permissions
        :param str sortby: Specifies sort by option,avaliable and default value :"created_time"
        :param str direction: Specifies sort direction,Available values: "asc",
        "desc", Default value ="desc"
        :param int offset: Specifies offset of the result, Default value = 1
        :param int limit: Specifies limit for results per page, Default value = 1000
        :param str sensor_info: Filter by sensor_info,Default = None
        :param str start_date: Specifies start date,Default = None
        :param str end_date: Specifies end date,Default = None
        :param str duration: Specifies alert history duration,Default = None
        :return: response of the api request
        :rtype: response object
        """
        try:
            # Building request url
            self.log.info("Forming alerts history endpoint url")
            endpoint = self.config["alerts_history_endpoint"]

            # Adding parameters
            endpoint = self._add_parameters_alert_history(
                endpoint, sortby=sortby, dirby=direction, offset=offset,
                limit=limit, sensor_info=sensor_info, start_date=start_date,
                end_date=end_date, duration=duration)
            self.log.info("Endpoint formed is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self.log.info(
                "response returned is:\n %s", response)
            return response

        except BaseException as error:
            self.log.error("%s %s: %s", const.EXCEPTION_ERROR,
                           SystemAlerts.get_alerts_history.__name__, error)
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

    # pylint: disable=too-many-arguments
    @staticmethod
    def _add_parameters_alert_history(endpoint, sortby="created_time", dirby="desc", offset=1,
                                      limit=1000, sensor_info=None, start_date=None, end_date=None,
                                      duration=None):

        params = []
        if sortby is not None:
            params.append("sortby={}".format(sortby))
        if dirby is not None:
            params.append("dir={}".format(dirby))
        if offset is not None:
            params.append("offset={}".format(offset))
        if limit is not None:
            params.append("limit={}".format(limit))
        if sensor_info is not None:
            params.append("sensor_info={}".format(sensor_info))
        if start_date is not None:
            params.append("start_date={}".format(start_date))
        if end_date is not None:
            params.append(" end_date={}".format(end_date))
        if duration is not None:
            params.append(" duration={}".format(duration))

        first_ele_flag = False
        for param in params:
            if param is not None:
                if not first_ele_flag:
                    endpoint = "{}?".format(endpoint)
                    first_ele_flag = True
                else:
                    endpoint = "{}&".format(endpoint)
                endpoint = "{}{}".format(endpoint, param)
        return endpoint

    @RestTestLib.authenticate_and_login
    def get_specific_alert_history(self, alert_id):
        """
        Get alert history for specific alert: Accessible to CSM users having
         monitor and manage permissions
        :param str alert_id: id of the alert
        :return: response of the api request
        :rtype: response object
        """
        try:
            # Building request url
            self.log.info("Forming the endpoint...")
            endpoint = self.config["alerts_history_endpoint"]

            endpoint = "{}/{}".format(endpoint, alert_id)
            self.log.info("Endpoint for getting alert history for alert id "
                          "%s is %s", alert_id, endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self.log.info(
                "response returned is:\n %s", response)
            return response

        except BaseException as error:
            self.log.error("%s %s: %s", const.EXCEPTION_ERROR,
                           SystemAlerts.get_specific_alert_history.__name__,
                           error)
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

    @RestTestLib.authenticate_and_login
    def get_alert_comments(self, alert_id):
        """
        Gets alert comments for specific alert: Accessible to CSM users having
        monitor and manage permissions
        :param str alert_id: id of the alert
        :return: response of the api request
        :rtype: response object
        """
        try:
            # Building request url
            self.log.info("Forming the endpoint")
            endpoint = self.config["alerts_endpoint"]

            endpoint = f"{endpoint}/{alert_id}/comments"
            self.log.info(
                "Endpoint for getting comments for alert %s is %s", alert_id,
                endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self.log.info(
                "response returned is:\n %s", response)
            return response

        except BaseException as error:
            self.log.error("%s %s: %s", const.EXCEPTION_ERROR,
                           SystemAlerts.get_alert_comments.__name__, error)
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

    @RestTestLib.authenticate_and_login
    def ack_all_unacknowledged_alerts(self, alert_id_list):
        """
        Function to acknowledge all unacknowledged alerts
        :param list alert_id_list: list of unacknowledged alerts
        :return: response of the api request
        :rtype: response object
        """
        try:
            # Building request url
            self.log.info(
                "Forming the request url ")
            endpoint = self.config["alerts_endpoint"]
            self.log.info("Endpoint is %s", endpoint)

            # Payload containing the list of unacknowledged alerts
            payload = alert_id_list

            # Fetching api response
            response = self.restapi.rest_call(
                "patch", json_dict=payload, endpoint=endpoint, headers=self.headers)
            self.log.info(
                "response returned is:\n %s", response)

            return response
        except BaseException as error:
            self.log.error("%s %s: %s", const.EXCEPTION_ERROR,
                           SystemAlerts.ack_all_unacknowledged_alerts.__name__,
                           error)
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error
