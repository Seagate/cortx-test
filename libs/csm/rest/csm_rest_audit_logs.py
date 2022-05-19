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
"""Test library for audit logs."""
import re
import tarfile
from pathlib import Path
import os
import shutil
import commons.errorcodes as err
from commons.exceptions import CTException
from commons.constants import Rest as const
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class RestAuditLogs(RestTestLib):
    """RestAuditLogs contains all the Rest Api calls for audit logs operations"""

    def __init__(self, component_csm="csm", component_s3="s3"):
        super(RestAuditLogs, self).__init__()
        self.component_csm = component_csm
        self.component_s3 = component_s3
        self.invalid_component = "invalid"

    @RestTestLib.authenticate_and_login
    def audit_logs_csm_show(self, params, invalid_component=False):
        """
        This method will show csm audit logs
        :param params: parameters for rest call(dictonary)
        :param invalid_component: invalid component
        possible values (True/False)
        :return: show csm audit rest call response
        """
        try:
            # Building request url
            self.log.info("Show audit logs for csm")
            if not invalid_component:
                endpoint = self.config["audit_logs_show_endpoint"].format(
                    self.component_csm)
            else:
                endpoint = self.config["audit_logs_show_endpoint"].format(
                    self.invalid_component)
            self.log.info("Endpoint for csm show audit logs is %s", endpoint)
            self.log.info("Params for csm show audit logs is %s", params)
            self.headers.update(self.config["Login_headers"])
            return self.restapi.rest_call("get",
                                          endpoint=endpoint,
                                          headers=self.headers,
                                          params=params)
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestAuditLogs.audit_logs_csm_show.__name__,
                           error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error) from error

    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-branches
    def verify_audit_logs_csm_show(self, params, expected_status_code=200,
                                   login_as="csm_admin_user", validate_expected_response=True,
                                   invalid_component=False):
        """
        This method will verify csm show audit logs
        :param params: parameters for rest call(dictonary)
        :param expected_status_code: expected status code to be verify
        :param login_as: The type of user you desire to login(default : csm_admin_user)
        :param validate_expected_response: Validate expected response(default : True)
        possible values (True/False)
        :param invalid_component: invalid component
        possible values (True/False)
        :return: Success(True/False)
        """
        try:
            response = self.audit_logs_csm_show(
                login_as=login_as, params=params, invalid_component=invalid_component)
            if response.status_code != expected_status_code:
                self.log.error(
                    "Response is not 200, Response=%s",
                    response.status_code)
                return False

            # Validating response value
            if validate_expected_response:
                response = response.json()
                pattern1 = ('csm_agent_audit', 'audit:', 'User:',
                            'Remote_IP:', 'Url:', 'Method:GET', 'User-Agent:', 'RC:')
                pattern2 = ('csm_agent_audit', 'audit:', 'Remote_IP:',
                            'Url:', 'Method:POST', 'User-Agent:', 'RC:')
                pattern3 = ('csm_agent_audit', 'audit:', 'Remote_IP:',
                            'Url:', 'Method:GET', 'User-Agent:', 'RC:')
                for element in response:
                    # Pattern 1 and pattern3 are valid in case of GET calls
                    # Pattern 2 is valid in case of POST calls
                    # Keywords in the pattern list should match and should be
                    # present in the log line of Audit Trail.
                    if 'Method:GET' in element:
                        retval = True
                        for i in pattern1:
                            if i not in element:
                                self.log.error(
                                    "Values does not match for get %s", element)
                                retval = False
                                break
                        # Pattern 1 did not match, check for pattern 3
                        if not retval:
                            for i in pattern3:
                                if i not in element:
                                    self.log.error(
                                        "Values does not match for get %s", element)
                                    return False

                    elif 'Method:POST' in element:
                        for i in pattern2:
                            if i not in element:
                                self.log.error(
                                    "Values does not match for post %s", element)
                                return False
            return True

        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestAuditLogs.verify_audit_logs_csm_show.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                error) from error

    @RestTestLib.authenticate_and_login
    def audit_logs_csm_download(self, params, invalid_component=False):
        """
        This method will download csm audit logs
        :param params: parameters for rest call(dictonary)
        :param invalid_component: invalid component
        possible values (True/False)
        :return: download csm audit rest call response
        """
        try:
            # Building request url
            self.log.info("Download audit logs for csm")
            if not invalid_component:
                endpoint = self.config["audit_logs_download_endpoint"].format(
                    self.component_csm)
            else:
                endpoint = self.config["audit_logs_download_endpoint"].format(
                    self.invalid_component)
            self.log.info(
                "Endpoint for csm download audit logs is %s", endpoint)

            self.headers.update(self.config["Login_headers"])
            return self.restapi.rest_call("get",
                                          endpoint=endpoint,
                                          headers=self.headers,
                                          params=params)
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestAuditLogs.audit_logs_csm_download.__name__,
                           error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error) from error

    # pylint: disable=too-many-arguments
    def verify_audit_logs_csm_download(self, params, expected_status_code=200,
                                       login_as="csm_admin_user", validate_expected_response=True,
                                       invalid_component=False, response_type=None):
        """
        This method will verify download csm audit logs
        :param params: parameters for rest call(dictonary)
        :param expected_status_code: expected status code to be verify
        :param login_as: The type of user you desire to login(default : csm_admin_user)
        :param validate_expected_response: Validate expected response(default : True)
        possible values (True/False)
        :param invalid_component: invalid component
        possible values (True/False)
        :param response_type: type of response(default : None)
        possible values (str)
        :return: Success(True/False)
        """
        try:
            response = self.audit_logs_csm_download(
                login_as=login_as, params=params, invalid_component=invalid_component)
            if response.status_code != expected_status_code:
                self.log.error(
                    "Response is not 200, Response=%s",
                    response.status_code)
                return False

            # Validating response value
            if validate_expected_response:
                if response_type:
                    return isinstance(response.text, response_type)
                response = response.json()
                exp_response = {
                    "Message": "Audit logs for csm downloaded Successfully."}
                if response != exp_response:
                    self.log.error("Values does not match ")
                    return False
            return True

        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestAuditLogs.verify_audit_logs_csm_download.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                error) from error

    @RestTestLib.authenticate_and_login
    def audit_logs_s3_show(self, params):
        """
        This method will show s3 audit logs
        :param params: parameters for rest call(dictonary)
        :return: show s3 audit rest call response
        """
        try:
            # Building request url
            self.log.info("Show audit logs for s3")
            endpoint = self.config["audit_logs_show_endpoint"].format(
                self.component_s3)
            self.log.info(
                "Endpoint for s3 show audit logs is %s", endpoint)

            self.headers.update(self.config["Login_headers"])
            return self.restapi.rest_call("get",
                                          endpoint=endpoint,
                                          headers=self.headers,
                                          params=params)
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestAuditLogs.audit_logs_s3_show.__name__,
                           error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error) from error

    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-branches
    def verify_audit_logs_s3_show(self, params, expected_status_code=200,
                                  login_as="csm_admin_user", validate_expected_response=True,
                                  bucket=None):
        """
        This method will verify s3 show audit logs
        :param params: parameters for rest call(dictonary)
        :param expected_status_code: expected status code to be verify
        :param login_as: The type of user you desire to login(default : csm_admin_user)
        :param validate_expected_response: Validate expected response(default : True)
        possible values (True/False)
        :param str bucket: bucket name(default: None)
        :return: Success(True/False)
        """
        try:
            verification_status = False
            response = self.audit_logs_s3_show(
                login_as=login_as, params=params)
            if response.status_code != const.SUCCESS_STATUS:
                self.log.error(
                    "Response is not 200, Response=%s",
                    response.status_code)
                return verification_status

            # Validating response value
            if validate_expected_response:
                self.log.info("Reading Audit log show API response...")
                response = response.json()
                for element in response["logs"]:
                    if bucket:
                        if bucket == element["bucket"]:
                            if element["operation"] == "REST.PUT.BUCKET":
                                self.log.info(
                                    "Verifying bucket specific parameters for"
                                    "bucket %s in the audit log", bucket)
                                verification_status = True
                                if element["signature_version"] != "SigV4":
                                    self.log.debug(
                                        "Operation parameter value returned is:"
                                        " %s", element)
                                    self.log.error(
                                        "Operation parameter value does not "
                                        "match with the expected Operation")
                                    verification_status = False
                                else:
                                    self.log.info(
                                        "Operation parameter value matched with"
                                        " the expected Operation")
                                if element["key"] != f"{bucket}/":
                                    self.log.debug(
                                        "Key parameter value returned is: %s", element["key"])
                                    self.log.error(
                                        "Key parameter value does not match with"
                                        " the expected Key")
                                    verification_status = False
                                else:
                                    self.log.info(
                                        "Key parameter value matched with the expected Key")
                                if f"PUT /{bucket}" not in element["request_uri"]:
                                    self.log.debug("Request URI parameter value"
                                                   " returned is: %s %s", element["request_uri"])
                                    self.log.error(
                                        "Request URI parameter value does not "
                                        "match with the expected Request URI")
                                    verification_status = False
                                else:
                                    self.log.info(
                                        "Request URI parameter value matched "
                                        "with the expected Request URI")
                                if (verification_status
                                        and element["http_status"] == expected_status_code):
                                    return verification_status

                                # Commenting below code till EOS-14998 is resolved #--------------#
                                # if item[10] != 200:
                                #     self.log.debug(
                                #         "HTTP status parameter value returned"
                                # " is: %s", item[10])
                                #     self.log.error(
                                #         "HTTP status parameter value does not"
                                # " match with the expected HTTP Status")
                                #     verification_status = False
                                # else:
                                #     self.log.info(
                                #         "HTTP status parameter value matched "
                                # "with the expected HTTP Status")
                                # if item[11] != "-":
                                #     self.log.debug(
                                #         "Error Code parameter value returned"
                                # " is: %s", item[11])
                                #     self.log.error(
                                #         "Error Code parameter value does not "
                                # "match with the expected Error Code")
                                #     verification_status = False
                                # else:
                                #     self.log.info(
                                #         "Error Code parameter value matched "
                                # "with the expected Error Code")
                                # if not verification_status:
                                #     self.log.error("Values does not match ")
                                #     return False

                        # self.log.info(
                        #     "Verifying parameters for all the logs in the S3 "
                        # "audit log")

                        # verification_status = True

                        # if not item[0]:
                        #     self.log.error(
                        #         "Bucket owner parameter value is not present")
                        #         self.log.debug(
                        #                 "Bucket owner parameter value "
                        # "returned is: %s", item[0])
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "Bucket owner parameter value is present")

                        # if "REST" not in item[6]:
                        #     self.log.debug(
                        #                 "Operation parameter value returned "
                        # "is: %s", item[6])
                        #     self.log.error(
                        #         "Operation parameter value does not match "
                        # "with the expected Operation")
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "Operation parameter value matched with the "
                        # "expected Operation")
                        # if item[16] != "-":
                        #     self.log.debug(
                        #         "Referrer parameter value returned is: %s",
                        # item[16])
                        #     self.log.error(
                        #         "Referrer parameter value does not match with"
                        # " the expected Referrer")
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "Referrer parameter value matched with the "
                        # "expected Referrer")
                        # if not item[17]:
                        #     self.log.debug(
                        #                 "User agent parameter value returned "
                        # "is: %s", item[17])
                        #     self.log.error(
                        #         "User agent parameter value nto present")
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "User agent parameter value is present")

                        # if item[-6] != "":
                        #     self.log.debug(
                        #                 "Version id parameter value returned "
                        # "is: %s", item[-6])
                        #     self.log.error(
                        #         "Version Id parameter value does not match "
                        # "with the expected Version Id")
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "Version Id parameter value matched with the "
                        # "expected Version Id")

                        # if item[-5] != "-":
                        #     self.log.debug(
                        #                 "Host Id parameter value returned is:"
                        # " %s", item[-5])
                        #     self.log.error(
                        #         "Host Id parameter value does not match with"
                        # " the expected Host Id")
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "Host Id parameter value matched with the "
                        # "expected Host Id")
                        # if item[-4] != "SigV4":
                        #     self.log.debug(
                        #                 "Signature Version parameter value "
                        # "returned is: %s", item[-4])
                        #     self.log.error(
                        #         "Signature Version parameter value does not "
                        # "match with the expected Signature Version")
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "Signature Version parameter value matched "
                        # "with the expected Signature Version")
                        # if item[-3] != "-":
                        #     self.log.debug(
                        #                 "Cipher Suite parameter value "
                        # "returned is: %s", item[-3])
                        #     self.log.error(
                        #         "Cipher Suite parameter value does not match "
                        # "with the expected Cipher Suite")
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "Cipher Suite parameter value matched with "
                        # "the expected Cipher Suite")
                        # if item[-2] != "AuthHeader":
                        #     self.log.debug(
                        #                 "Authentication type parameter value"
                        # " returned is: %s", item[-2])
                        #     self.log.info(
                        #         "Authentication type parameter value does not"
                        # " match with the expected Authentication Type")
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "Authentication type parameter value matched "
                        # "with the expected Authentication Type")
                        # if not verification_status:
                        #     self.log.error("Values does not match ")
                        #     return False
                        # if not item[-1]:
                        #     self.log.debug(
                        #                 "Host Header parameter value returned"
                        # " is: %s", item[-1])
                        #     self.log.error(
                        #         "Host Header parameter value is not present")
                        #     verification_status = False
                        # else:
                        #     self.log.info(
                        #         "Host Header parameter value is present")
                        # if not verification_status:
                        #     self.log.error("Values does not match ")
                        #     return False

            return True
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestAuditLogs.verify_audit_logs_s3_show.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                error) from error

    @RestTestLib.authenticate_and_login
    def audit_logs_s3_download(self, params):
        """
        This method will download s3 audit logs
        :param params: parameters for rest call(dictonary)
        :return: download s3 audit rest call response
        """
        try:
            # Building request url
            self.log.info("Download audit logs for s3")
            endpoint = self.config["audit_logs_download_endpoint"].format(
                self.component_s3)
            self.log.info(
                "Endpoint for s3 download audit logs is %s", endpoint)

            self.headers.update(self.config["Login_headers"])
            return self.restapi.rest_call("get",
                                          endpoint=endpoint,
                                          headers=self.headers,
                                          params=params)
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestAuditLogs.audit_logs_s3_download.__name__,
                           error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error) from error

    # pylint: disable=too-many-arguments
    def verify_audit_logs_s3_download(self, params, expected_status_code=200,
                                      login_as="csm_admin_user", validate_expected_response=True,
                                      response_type=None):
        """
        This method will verify download s3 audit logs
        :param params: parameters for rest call(dictonary)
        :param expected_status_code: expected status code to be verify
        :param login_as: The type of user you desire to login(default : csm_admin_user)
        :param validate_expected_response: Validate expected response(default : True)
        possible values (True/False)
        :param response_type: type of response(default : None)
        possible values (str)
        :return: Success(True/False)
        """
        try:
            response = self.audit_logs_s3_download(
                login_as=login_as, params=params)
            if response.status_code != expected_status_code:
                self.log.error(
                    "Response is not 200, Response=%s",
                    response.status_code)
                return False

            # Validating response value
            if validate_expected_response:
                if response_type:
                    return isinstance(response.text, response_type)
                response = response.json()
                exp_response = {
                    "Message": "Audit logs for s3 downloaded Successfully."}
                if response != exp_response:
                    self.log.error("Values does not match ")
                    return False
            return True

        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestAuditLogs.verify_audit_logs_s3_download.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                error) from error

    # pylint: disable-msg=too-many-branches
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-return-statements
    def verify_audit_logs_show_download(self, audit_log_show_response, audit_log_download_response):
        """
        This function will verify the audit log show and audit log download contents match
        :param audit_log_show_response: response returned from audit logs show api
        :type audit_log_show_response: api response
        :param audit_log_download_response: response returned from audit logs show api
        :type audit_log_download_response: api response
        :return: True/False
        :rtype: bool
        """
        try:
            self.log.info(
                "Reading the file name from the audit log download api response")
            filename = []
            cndp = audit_log_download_response.headers.get('content-disposition')
            if not cndp:
                self.log.info("No file to download")
                return False
            else:
                filename = re.findall('filename=(.+)', cndp)
            if len(filename) == 0:
                self.log.info("No file to download")
                return False

            filename[0] = filename[0].strip('\"')
            self.log.info("The filename is : %s", filename[0])

            self.log.info("Downloading the tar file to tempdownload folder")
            download_folder_path = f"{Path.home()}/tempdownload"
            if not os.path.exists(download_folder_path):
                os.mkdir(download_folder_path)
            file_path = f"{download_folder_path}/{filename[0]}"
            file_obj = open(file_path, 'wb')
            file_obj.write(audit_log_download_response.content)
            file_obj.close()

            self.log.info(
                "Path to the downloaded file is: %s", file_path)

            self.log.info("File that will be extracted will be txt file")
            base = os.path.basename(file_path)
            file_name = os.path.splitext(base)[0]
            file_name = os.path.splitext(file_name)[0]
            self.log.info(file_name)

            extract_file = f"{file_name}.txt"
            self.log.info("File to be extracted is :%s", extract_file)

            self.log.info("Extracting the file")
            downloaded_tar_file = tarfile.open(file_path)
            downloaded_tar_file.extract(extract_file, download_folder_path)
            downloaded_tar_file.close()

            self.log.info("Reading the txt file content into a list")
            text_file_path = f"{download_folder_path}/{extract_file}"
            text_file = open(text_file_path, "r")
            extracted_file_content = text_file.read().splitlines()
            text_file.close()

            self.log.info("audit_log_show_response.json() length is: %s",
                          audit_log_show_response.json()['total_records'])
            self.log.info("extracted_file_content length is: %s",
                          len(extracted_file_content))

            self.log.info(
                "Comparing the contents of audit log show api and audit log download api response")
            if audit_log_show_response.json()['total_records'] == len(extracted_file_content):
                if audit_log_show_response.json() == extracted_file_content:
                    self.log.info(
                        "The audit log show api content and audit log download"
                        " api content content match exactly! ")
                    self.log.info(
                        "Deleting the files and the temporary directory...")
                    shutil.rmtree(download_folder_path)
                    return True
                else:
                    self.log.info(
                        "Ignoring the first 2 and that last 2 records from show"
                        " api response and verifying if the remaining ones match")
                    log_content = audit_log_show_response.json(
                    )['logs'][2:audit_log_show_response.json()['total_records'] - 3]
                    result = True
                    for log_line in log_content:
                        if log_line['request_id'] not in extracted_file_content:
                            self.log.error("Couldnt find %s from json in downloaded file", log_line)
                            result = False

                    # if all(x in extracted_file_content for x in log_content):
                    if result:
                        self.log.info(
                            "The audit log show api content and audit log"
                            " download api content content match exactly! ")
                        self.log.info(
                            "Deleting the files and the temporary directory...")
                        shutil.rmtree(download_folder_path)
                        return True
                    else:
                        self.log.debug("Audit log show API response is: %s",
                                       audit_log_show_response.json())
                        self.log.debug("Audit log download API response is: %s",
                                       extracted_file_content)
                        self.log.error("Error: Logs did not match!!")
                        self.log.info(
                            "Deleting the files and the temporary directory...")
                        shutil.rmtree(download_folder_path)
                        return False
            val = 0
            if audit_log_show_response.json()['total_records'] != len(extracted_file_content):
                if audit_log_show_response.json()['total_records'] > len(extracted_file_content):
                    self.log.info(
                        "The audit log show response content count is greater "
                        "than audit log download content count. Comparing the "
                        "content of audit log download with audit log show "
                        "content ...")
                    for i in range(0, len(extracted_file_content)):
                        for j in range(0, audit_log_show_response.json()['total_records']):
                            if extracted_file_content[i] == audit_log_show_response.json()[j]:
                                val = i + 1
                                break
                    if (val == len(extracted_file_content) or
                            val == audit_log_show_response.json()['total_records']):
                        self.log.info(
                            "The audit log download content match with the "
                            "audit log show api content")
                        self.log.info(
                            "Deleting the files and the temporary directory...")
                        shutil.rmtree(download_folder_path)
                        return True
                    else:
                        self.log.debug("Audit log show API response is: %s",
                                       audit_log_show_response.json())
                        self.log.debug("Audit log download API response is: %s",
                                       extracted_file_content)
                        self.log.error("Error: Logs did not match!!")
                        self.log.info(
                            "Deleting the files and the temporary directory...")
                        shutil.rmtree(download_folder_path)
                        return False
                if len(extracted_file_content) > audit_log_show_response.json()['total_records']:
                    self.log.info(
                        "The audit log download response content count is "
                        "greater than audit log show content count. Comparing "
                        "the content of audit log show with audit log download "
                        "content ...")
                    for i in range(0, audit_log_show_response.json()['total_records']):
                        for j in range(0, len(extracted_file_content)):
                            if extracted_file_content[j] == audit_log_show_response.json()[i]:
                                val = i + 1
                                break
                    if (val == len(extracted_file_content) or
                            val == audit_log_show_response.json()['total_records']):
                        self.log.info(
                            "The audit log show api content match with the "
                            "audit log download api content")
                        self.log.info(
                            "Deleting the files and the temporary directory...")
                        shutil.rmtree(download_folder_path)
                        return True
                    else:
                        self.log.debug("Audit log show API response is: %s",
                                       audit_log_show_response.json())
                        self.log.debug("Audit log download API response is: %s",
                                       extracted_file_content)
                        self.log.error("Error: Logs did not match!!")
                        self.log.info(
                            "Deleting the files and the temporary directory...")
                        shutil.rmtree(download_folder_path)
                        return False
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestAuditLogs.verify_audit_logs_show_download.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                error) from error

    def verify_csm_audit_logs_contents(self, response_log, str_search):
        """
        This function will verify the csm audit log show contents match for given users
        :param response_log: will take response from csm audit logs show
        :param str_search will take users to search in csm audit logs
        """
        response = []
        result = False
        for string in str_search:
            for item in response_log['logs']:
                if item['payload']:
                    if string in item.get('payload'):
                        result = True
                        break
            response.append(result)
        if result:
            self.log.info("CSM Audit logs contains the entries for %s user", str_search)
        else:
            self.log.error("CSM Audit logs does not contain the entries for %s user", str_search)
        return response

    def verify_s3_audit_logs_contents(self, response_log, str_search):
        """
        This function will verify the s3 audit log show contents match for given bucket or object
        :param response_log: will take response from s3 audit logs show
        :param str_search will take bucket or object to search in s3 audit logs
        """
        response = []
        result = False
        for string in str_search:
            for item in response_log['logs']:
                if string in item.get('key'):
                    result = True
                    break
                if string in item.get('bucket'):
                    result = True
                    break
            response.append(result)
        if result:
            self.log.info("S3 Audit logs contains the entries for %s", str_search)
        else:
            self.log.error("S3 Audit logs does not contain the entries for %s", str_search)
        return response
