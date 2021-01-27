"""Test library for System Health related operations.
   Author: Divya Kachhwaha
"""
import time
import json
import datetime
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from commons.utils import config_utils
from commons.helpers.node_helper import Node
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib, AlertType
from commons.constants import Ras as ras_cons

class SystemAlerts(RestTestLib):
    """SystemAlerts contains all the Rest API calls for system health related operations"""

    def __init__(self):
        """
        Initialize the rest api
        """
        super(SystemAlerts, self).__init__()
        main_conf = config_utils.read_yaml("config\common_config.yaml")[1]
        self.node_obj = Node(main_conf["server_hostname"]+main_conf["host_domain"],
                                    main_conf["server_username"],
                                    main_conf["server_password"])
    @RestTestLib.authenticate_and_login
    def get_alerts(self, alert_id=None, acknowledged=None, resolved=None,
                   show_active=None, sortby="created_time", dir="desc", offset=1, limit=10, severity=None):
        """
        Gets Alerts: Accessible to CSM users having monitor and manage permissions
        """
        try:
            # Building request url
            self._log.info("Reading alerts...")
            endpoint = self.config["alerts_endpoint"]
            # Adding parameters
            endpoint = self._add_parameters(
                endpoint, alert_id, acknowledged, resolved, show_active, sortby, dir, offset, limit, severity)
            self._log.info("Endpoint for reading alert is {}".format(endpoint))
            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)

            self._log.info(
                "response returned is:\n {}".format(response))

            return response

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                SystemAlerts.get_alerts.__name__,
                error))
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    @RestTestLib.authenticate_and_login
    def edit_alerts(self, alert_id, ack=True, comment="By Script", ack_key="acknowledged", comment_key="comments"):
        """
        TODO: Comment part is not working
        Gets Alerts: Accessible to CSM users having monitor and manage permissions
        """
        try:
            # Building request url
            self._log.info("Reading alerts...")
            endpoint = self.config["alerts_endpoint"]
            # Adding parameters
            endpoint = "{}/{}".format(endpoint, alert_id)
            self._log.info("Endpoint for reading alert is {}".format(endpoint))
            # Payload
            payload = {ack_key: ack, comment_key: comment}
            # Fetching api response
            response = self.restapi.rest_call(
                "patch", json_dict=payload, endpoint=endpoint, headers=self.headers)

            self._log.info(
                "response returned is:\n {}".format(response))

            return response

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                SystemAlerts.edit_alerts.__name__,
                error))
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def _add_parameters(self, endpoint, alert_id=None, acknowledged=None,
                        resolved=False, show_active=None, sortby="created_time", dirby="desc",
                        offset=1, limit=10, severity=None):
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
        data = response.json()
        alert_ids = []
        for entry in data["alerts"]:
            alert_ids.append(entry['alert_uuid'])
        self._log.info("Alert IDs detected are : ", alert_ids)

        return alert_ids

    def ack_all_alerts(self):
        # Read alerts which are not acknowledged
        response = self.get_alerts(acknowledged=False, limit=None)
        if response.json() == []:
            self._log.info("All alerts are acknowledged. No alerts to ack")
        else:
            self._log.debug(response.json())
        # Extract the alert IDs
        alert_ids = self.extract_alert_ids(response)
        # Ack each alert IDs
        for alert_id in alert_ids:
            self._log.info("Acknowledging the alert ID : {}".format(alert_id))
            self.edit_alerts(alert_id, ack=True)

    def verify_csm_response(self, starttime, alert_type, resolved, *response_checks):
        """Read the CSM alerts from starttime and verify the resolved
        and extended information

        :param starttime: time from which alerts should be considered for
         verification
        :param resolved: expected resolved state
        :return [bool]: True / False based on whether the response matched
        expected results
        """
        starttime = int(starttime)
        self._log.info("Start Time : {}".format(starttime))
        self._log.info("Extended information to be checked : {}".format(
            response_checks))
        self._log.info("CSM: Verifying the new Fault is reported...")
        alert_ids = self.get_alerts_id_after(starttime)
        if alert_ids:
            self._log.info("CSM: New alerts detected are {}".format(alert_ids))
        else:
            self._log.error("No New Alerts Detected")
            return False

        for alert_id in alert_ids:
            response = self.get_alerts(alert_id)
            if response.status_code == const.SUCCESS_STATUS:
                self._log.info(
                    "Alert ID {} details from Rest API".format(response))
                resp_flag = True
            else:
                self._log.error("Couldn't read the alert details from Alert ID"
                                f"{alert_id}")
                resp_flag = False

            match_found = True
            if resp_flag:
                alert_info = response.text
                json_response = response.json()
                self._log.info("Response info of the Alert ID {} is ".format(
                    alert_info))
                if (resolved == json_response['resolved']) and (alert_type in
                                                                alert_info):
                    self._log.info("Alert type check Passed for ", alert_id)
                    self._log.info("Resolved check Passed for ", alert_id)
                    for arg in response_checks:
                        if str(arg) in alert_info:
                            self._log.info("Verified {} in the response of "
                                           "alert ID {}".format(arg, alert_id))
                        else:
                            self._log.error("Couldn't find {} in the response "
                                            "of alert ID {}".format(arg, alert_id))
                            match_found = False
                            break

                    if match_found:
                        self._log.info(f"{alert_info}")
                        self._log.info(f"Found match for {response_checks}")
                        return True

        self._log.error("Couldn't find matching alert")
        return False

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
        else:
            starttime = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(starttime))
            self._log.info("Alerts generated after {} are : {}".format(
                starttime, alert_ids))
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
            self._log.info("Reading alerts...")
            endpoint = self.config["alerts_endpoint"]

            self._log.info("Forming the endpoint...")
            endpoint = "{}/{}/comments".format(endpoint, alert_id)
            self._log.info("Endpoint for reading alert is {}".format(endpoint))
            payload = {"comment_text": comment_text}

            # Fetching api response
            self._log.info("Fetching the response...")
            self.headers.update(const.CONTENT_TYPE)
            response = self.restapi.rest_call(
                request_type="post", endpoint=endpoint, data=json.dumps(payload), headers=self.headers)

            self._log.info(
                "response returned is:\n {}".format(response))

            return response
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                SystemAlerts.add_comment_to_alerts.__name__,
                error))
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0])

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
            self._log.info("Getting the alerts")
            response_get = self.get_alerts(login_as=user)

            if response_get.status_code == self.success_response:
                alert_id_index_list = [i for i in range(0, len(response_get.json()["alerts"])) if response_get.json()[
                    "alerts"][i]["alert_uuid"] == alert_id]
                alert_id_index = alert_id_index_list[0]

                comment_id_index_list = [j for j in range(0, len(response_get.json()["alerts"][alert_id_index]["comments"])) if response_get.json()[
                    "alerts"][alert_id_index]["comments"][j]["comment_id"] == response_alert_comment_added["comment_id"]]
                comment_id_index = comment_id_index_list[0]

                self._log.info("Converting utc time to timestamp...")

                created_time = datetime.datetime.strptime(response_get.json(
                )["alerts"][alert_id_index]["comments"][comment_id_index]["created_time"], "%Y-%m-%dT%H:%M:%S.%f%z")

                timestamp = datetime.datetime.timestamp(created_time)

                self._log.info("Replacing the utc time in the get response {} wih the timestamp {} for comparison".format(response_get.json()[
                    "alerts"][alert_id_index]["comments"][comment_id_index]["created_time"], int(timestamp)))
                resp_obj = response_get.json()
                resp_obj["alerts"][alert_id_index]["comments"][comment_id_index]["created_time"] = int(
                    timestamp)

                self._log.info(
                    "Verifying the comment that was added and that was read from GET api")

                if resp_obj["alerts"][alert_id_index]["comments"][comment_id_index] == response_alert_comment_added:
                    return True
                else:
                    self._log.info("Error: Comment was not added")
                    return False
            else:
                self._log.info(
                    "Get alerts returned non-success response: {}".format(response_get.status_code))
                return False
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                SystemAlerts.verify_added_alert_comment.__name__,
                error))
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0])

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
        util_obj = utility.Utility()
        expected_status = 200

        self._log.info("Acknowledging existing alerts...")
        self.ack_all_alerts()
        self._log.info("Get alerts...")
        response = self.get_alerts(**kwargs)
        self._log.info(f"Expected status Code : {expected_status}")
        self._log.info(f"Actual status Code : {response.status_code}")
        if response.status_code != expected_status:
            self._log.error(
                "Failed to Get alert details before alert is generated")
            return False
        before_alert_ids = self.extract_alert_ids(response)
        self._log.info(f"Before Alert IDs: {before_alert_ids}")

        response = self.get_alerts(acknowledged=False, resolved=False)
        pre_alerts = self.extract_alert_ids(response)

        self._log.info("Creating alert...")
        local_path = ras_cons.TELNET_OP_PATH
        remote_path = ras_cons.REMOTE_TELNET_PATH
        self._log.info(f"Copying file {local_path} to {remote_path}")
        copy_res = util_obj.copy_file_to_remote(local_path=local_path,
                                                remote_file_path=remote_path,
                                                shell=False)
        if not copy_res[0]:
            self._log.info(f"Failed to copy file Error:{copy_res[1]}")
            return False
        resp = alert_api_obj.generate_alert(
            eval('AlertType.{}'.format(alert_type)))
        if not resp[0]:
            self._log.error("Failed to created alert")
            return False

        generared_alert = False
        starttime = time.time()
        timediff = 0
        while (timediff < alert_timeout):
            time.sleep(10)
            self._log.info("Reading alerts details...")
            response = self.get_alerts(acknowledged=False, resolved=False)
            post_alerts = self.extract_alert_ids(response)
            new_alerts = list(set(post_alerts)-set(pre_alerts))
            if new_alerts != []:
                generared_alert = True
                break
            timediff = time.time()-starttime
        if generared_alert:
            self._log.info(f"Successfully created alerts : {new_alerts}")
            self._log.info(f"Alert reported on CSM after {timediff} seconds")
        else:
            self._log.error("Alert is not reported on CSM.")
            return False

        self._log.info("Reading alerts details...")
        response = self.get_alerts(**kwargs)
        self._log.info(f"Expected status Code : {expected_status}")
        self._log.info(f"Actual status Code : {response.status_code}")
        if response.status_code != expected_status:
            self._log.error(
                "Failed to Get alert details after alert is generated.")
            return False
        after_alert_ids = self.extract_alert_ids(response)
        self._log.info(f"After alert IDs: {after_alert_ids}")
        return new_alerts, before_alert_ids, after_alert_ids

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
        util_obj = utility.Utility()
        expected_status = 200

        self._log.info("Get alerts...")
        response = self.get_alerts(**kwargs)
        self._log.info(f"Expected status Code : {expected_status}")
        self._log.info(f"Actual status Code : {response.status_code}")
        if response.status_code != expected_status:
            self._log.error(
                "Failed to Get alert details before alert is generated")
            return False
        before_alert_ids = self.extract_alert_ids(response)
        self._log.info(f"Pre Alert IDs: {before_alert_ids}")

        local_path = ras_cons.TELNET_OP_PATH
        remote_path = ras_cons.REMOTE_TELNET_PATH
        self._log.info(f"Copying file {local_path} to {remote_path}")
        copy_res = util_obj.copy_file_to_remote(local_path=local_path,
                                                remote_file_path=remote_path,
                                                shell=False)
        if not copy_res[0]:
            self._log.info(f"Failed to copy file Error:{copy_res[1]}")
            return False

        response = self.get_alerts(resolved=False)
        pre_resolve = self.extract_alert_ids(response)

        self._log.info("Resolving alert...")
        resp = alert_api_obj.generate_alert(
            eval('AlertType.{}'.format(resolve_type)))
        if not resp[0]:
            self._log.error("Failed to resolve alert")
            return False

        resolved_alert = False
        starttime = time.time()
        timediff = 0
        while (timediff < alert_timeout):
            time.sleep(10)
            self._log.info("Reading alerts details...")
            response = self.get_alerts(resolved=False)
            post_resolve = self.extract_alert_ids(response)
            new_alerts = list(set(post_resolve)-set(pre_resolve))
            if new_alerts != []:
                resolved_alert = True
                break
            timediff = time.time()-starttime
        if resolved_alert:
            self._log.info("Successfully resolved alert")
            self._log.info(f"Alert reported on CSM after {timediff} seconds")
        else:
            self._log.error("Alert is not reported on CSM.")
            return False

        self._log.info("Reading alerts details...")
        response = self.get_alerts(**kwargs)
        self._log.info(f"Expected status Code : {expected_status}")
        self._log.info(f"Actual status Code : {response.status_code}")
        if response.status_code != expected_status:
            self._log.error(
                "Failed to Get alert details after alert is generated")
            return False

        after_alert_ids = self.extract_alert_ids(response)
        self._log.info(f"Post alert IDs: {after_alert_ids}")
        return before_alert_ids, after_alert_ids
        
    @RestTestLib.authenticate_and_login
    def get_alerts_history(self, sortby="created_time", dir="desc", offset=1, limit=1000, sensor_info=None, start_date=None, end_date=None, duration=None):
        """
        Get alert history: Accessible to CSM users having monitor and manage permissions
        :param str sortby: Specifies sort by option,avaliable and default value :"created_time"
        :param str dir: Specifies sort direction,Available values: "asc", "desc", Default value ="desc"
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
            self._log.info("Forming alerts history endpoint url")
            endpoint = self.config["alerts_history_endpoint"]

            # Adding parameters
            endpoint = self._add_parameters_alert_history(
                endpoint, sortby=sortby, dirby=dir, offset=offset, limit=limit, sensor_info=sensor_info, start_date=start_date, end_date=end_date, duration=duration)
            self._log.info("Endpoint formed is {}".format(endpoint))

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self._log.info(
                "response returned is:\n {}".format(response))
            return response

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                SystemAlerts.get_alerts_history.__name__,
                error))
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def _add_parameters_alert_history(self, endpoint, sortby="created_time", dirby="desc", offset=1, limit=1000, sensor_info=None, start_date=None, end_date=None, duration=None):

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
        Get alert history for specific alert: Accessible to CSM users having monitor and manage permissions
        :param str alert_id: id of the alert 
        :return: response of the api request
        :rtype: response object
        """
        try:
            # Building request url
            self._log.info("Forming the endpoint...")
            endpoint = self.config["alerts_history_endpoint"]

            endpoint = "{}/{}".format(endpoint, alert_id)
            self._log.info("Endpoint for getting alert history for alert id {} is {}".format(
                alert_id, endpoint))

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self._log.info(
                "response returned is:\n {}".format(response))
            return response

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                SystemAlerts.get_specific_alert_history.__name__,
                error))
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    @RestTestLib.authenticate_and_login
    def get_alert_comments(self, alert_id):
        """
        Gets alert comments for specific alert: Accessible to CSM users having monitor and manage permissions
        :param str alert_id: id of the alert 
        :return: response of the api request
        :rtype: response object
        """
        try:
            # Building request url
            self._log.info("Forming the endpoint")
            endpoint = self.config["alerts_endpoint"]

            endpoint = f"{endpoint}/{alert_id}/comments"
            self._log.info(
                "Endpoint for getting comments for alert {} is {}".format(alert_id, endpoint))

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self._log.info(
                "response returned is:\n {}".format(response))
            return response

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                SystemAlerts.get_alert_comments.__name__,
                error))
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0])

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
            self._log.info(
                "Forming the request url ")
            endpoint = self.config["alerts_endpoint"]
            self._log.info("Endpoint is {}".format(endpoint))

            # Payload containing the list of unacknowledged alerts
            payload = alert_id_list

            # Fetching api response
            response = self.restapi.rest_call(
                "patch", json_dict=payload, endpoint=endpoint, headers=self.headers)
            self._log.info(
                "response returned is:\n {}".format(response))

            return response
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                SystemAlerts.ack_all_unacknowledged_alerts.__name__,
                error))
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0])
