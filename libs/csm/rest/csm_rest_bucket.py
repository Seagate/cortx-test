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
"""Test library for s3 bucket operations."""
import time
import json
from string import Template
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from commons.utils import config_utils
from libs.csm.rest.csm_rest_test_lib import RestTestLib
class RestS3Bucket(RestTestLib):
    """RestS3Bucket contains all the Rest Api calls for s3 account operations"""

    def __init__(self):
        super(RestS3Bucket, self).__init__()
        self.recently_created_s3_bucket = None
        template_payload = Template(const.BUCKET_PAYLOAD)
        self._bucket_payload = {
            "valid": template_payload.substitute(value=int(time.time())),
            "bucket_name_less_than_three_char": template_payload.substitute(value=""),
            "bucket_name_more_than_63_char": template_payload.substitute(value="n" * 66),
            "start_with_underscore": "{\"bucket_name\":\"_buk\"}",
            "start_with_uppercase": "{\"bucket_name\":\"Buket1\"}",
            "ip_address": "{\"bucket_name\":\"1.1.1.1\"}",
            "duplicate": "{\"bucket_name\":\"duplicate\"}",
            "invalid": "{\"bucket_name\":\"\"}",
        }
        self.user_data = None

    @RestTestLib.authenticate_and_login
    def create_s3_bucket(self, bucket_type):
        """
        This function will create new s3 bucket
        :param bucket_type: type of bucket required
        :return: response of create bucket
        """
        try:
            # Building request url
            self.log.debug("Create s3 bucket ...")
            endpoint = self.config["s3_bucket_endpoint"]
            self.log.debug("Endpoint for s3 accounts is %s", endpoint)

            # Collecting required payload to be added for request
            user_data = self._bucket_payload[bucket_type]
            self.log.debug("Payload for s3 bucket is %s", user_data)
            self.headers.update(self.config["Login_headers"])
            self.recently_created_s3_bucket = user_data

            # Fetching api response
            return self.restapi.rest_call(
                "post",
                endpoint=endpoint,
                data=user_data,
                headers=self.headers)

        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3Bucket.create_s3_bucket.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error) from error

    @RestTestLib.authenticate_and_login
    def list_all_created_buckets(self):
        """
        This function will list down all created buckets
        :return: Returns created bucket list
        """
        try:
            # Building request url
            self.log.debug("Try to fetch all s3 buckets ...")
            endpoint = self.config["s3_bucket_endpoint"]
            self.log.debug("Endpoint for s3 bucket is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(
                "get", endpoint=endpoint, headers=self.headers)

            return response
        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3Bucket.list_all_created_buckets.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error) from error

    @RestTestLib.authenticate_and_login
    def delete_s3_bucket(self, bucket_name):
        """
        This function will delete the required bucket
        :param bucket_name: Bucket name to be deleted
        :return: response delete s3 bucket
        """
        try:
            # Building request url
            self.log.debug("Try to delete s3 bucket : %s", bucket_name)
            endpoint = "{}/{}".format(
                self.config["s3_bucket_endpoint"], bucket_name)
            self.log.debug("Endpoint for s3 accounts is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(
                "delete", endpoint=endpoint, headers=self.headers)

            return response
        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3Bucket.delete_s3_bucket.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error) from error

    def create_and_verify_new_bucket(
            self,
            expect_status_code,
            bucket_type="valid",
            login_as="s3account_user"):
        """
        This function will create and verify that new created bucket
        :param bucket_type: type of bucket required (default : valid)
        possible values (valid, bucket_name_less_than_three_char,
        bucket_name_more_than_63_char, start_with_underscore,
        start_with_uppercase, ip_address, duplicate, invalid)
        :param expect_status_code: expected status code to be verify
        :param login_as: The type of user you desire to login(default : s3account_user)
        possible values (csm_admin_user, s3account_user, csm_user_manage, csm_user_monitor)
        :return: Success(True)/Failure(False)
        """
        try:
            # Checking for user type
            if bucket_type not in self._bucket_payload:
                self.log.error("Invalid user type")
                return False

            # Fetching and verifying response
            response = self.create_s3_bucket(
                bucket_type=bucket_type, login_as=login_as)
            if bucket_type != "valid":
                if bucket_type == "duplicate":
                    response = self.create_s3_bucket(
                        bucket_type="duplicate", login_as=login_as)
                self.log.debug(
                    "Checking the response for %s", bucket_type)
                return response.status_code == expect_status_code

            if (not response) or response.status_code != expect_status_code:
                self.log.error("Response is not 200")
                return False
            response = response.json()

            # Validating response value
            if response["bucket_name"] != json.loads(
                self.recently_created_s3_bucket)["bucket_name"]:
                self.log.error("Values does not match ")
                return False
            list_response = self.list_all_created_buckets(
                login_as=login_as).json()["buckets"]
            response = {"name": response[const.BUCKET_NAME]}
            return any(config_utils.verify_json_response(actual_result, response)
                       for actual_result in list_response)
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3Bucket.create_and_verify_new_bucket.__name__,
                error)
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error
                    ) from error

    def list_and_verify_bucket(
            self,
            expect_no_user=False,
            login_as="s3account_user"):
        """
        This function will list and verity s3 buckets
        :param expect_no_user: Newly created account scenario
        :param login_as: The type of user you desire to login(default : s3account_user)
        possible values (csm_admin_user, s3account_user, csm_user_manage, csm_user_monitor)
        :return: Success/Failure
        """
        try:
            response = self.list_all_created_buckets(login_as=login_as)
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self.log.error("Response is not 200")
                return False
            response = response.json()

            # Verifying response key
            if const.BUCKET not in response:
                self.log.error("Bucket key is not present")
                return False

            # Checking for not "no user" scenario
            if len(response[const.BUCKET]) == 0 or expect_no_user:
                self.log.warning("Buckets present till now is : %s",
                    len(response[const.BUCKET]))
                return len(response[const.BUCKET]) == 0 and expect_no_user

            # Checking format
            if not all(
                    const.NAME in key for key in response[const.BUCKET]):
                self.log.error("Invalid for mat of the json")
                return False

            return all(isinstance(value[const.NAME], str)
                       for value in response[const.BUCKET])
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3Bucket.list_and_verify_bucket.__name__,
                error)
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error
                    ) from error

    def delete_and_verify_new_bucket(
            self,
            expect_status_code,
            bucket_type="valid",
            login_as="s3account_user"):
        """
        This function will delete and verify that bucket
        :param bucket_type: type of bucket required (default : valid)
        possible values (does-not-exist, valid)
        :param expect_status_code: expected status code to be verify
        :param login_as: The type of user you desire to login(default : s3account_user)
        possible values (csm_admin_user, s3account_user, csm_user_manage, csm_user_monitor)
        :return: Success(True)/Failure(False)
        """
        try:
            # Checking special conditions
            if bucket_type == "does-not-exist":
                self.log.debug(
                    "Checking response for bucket name does not exist")
                response = self.delete_s3_bucket(
                    bucket_name="does-not-exist", login_as=login_as)
                return response.status_code == expect_status_code

            # Fetching and verifying response
            self.create_s3_bucket(bucket_type=bucket_type, login_as=login_as)
            bucket_name = json.loads(
                self.recently_created_s3_bucket)[
                const.BUCKET_NAME]
            response = self.delete_s3_bucket(
                bucket_name=bucket_name, login_as=login_as)

            if (not response) or response.status_code != expect_status_code:
                self.log.error("Response is not 200")
                return False
            response = json.loads(self.recently_created_s3_bucket)
            list_response = self.list_all_created_buckets(
                login_as=login_as).json()["buckets"]
            response = {"name": response[const.BUCKET_NAME]}
            return all(
                config_utils.verify_json_response(
                    actual_result,
                    response) is False for actual_result in list_response)
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3Bucket.delete_and_verify_new_bucket.__name__,
                error)
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error
                                ) from error

    @RestTestLib.authenticate_and_login
    def create_invalid_s3_bucket(self, bucket_name):
        """
        This function will verify invalid s3 bucket creation
        :param bucket_name: type of bucket required
        :return: response of create bucket
        :rtype: response object
        """
        try:
            # Building request url
            self.log.debug("Create s3 bucket ...")
            endpoint = self.config["s3_bucket_endpoint"]
            self.log.debug("Endpoint for s3 accounts is %s",endpoint)

            # Collecting required payload to be added for request
            user_data = json.loads(self._bucket_payload["invalid"])
            user_data["bucket_name"] = bucket_name

            self.log.debug("Payload for s3 bucket is %s", user_data)
            self.headers.update(self.config["Login_headers"])

            # Fetching api response
            return self.restapi.rest_call("post", endpoint=endpoint,
                            data=json.dumps(user_data), headers=self.headers)
        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3Bucket.create_invalid_s3_bucket.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error

    @RestTestLib.authenticate_and_login
    def create_s3_bucket_for_given_account(self, bucket_name, account_name, account_password,
                                           bucket_type="valid"):
        """
        This function will create new s3 bucket for the given user_name.
        :param bucket_name: Bucket name
        :param account_name: S3 account name under which we want to create new bucket
        :param account_password: S3 account password under which we want to create new bucket
        :param bucket_type: type of bucket required
        :return: response of create bucket
        """
        try:
            self.log.debug("Creating new S3 bucket under {}".format(account_name))
            endpoint = self.config["s3_bucket_endpoint"]
            self.log.debug("Endpoint for S3 bucket creation is {}".format(endpoint))
            headers = self.get_headers(account_name, account_password)
            user_data = "{{\"{}\":\"{}\"}}".format(
                "bucket_name", bucket_name)

            # Fetching api response
            response = self.restapi.rest_call("post", endpoint=endpoint, data=user_data,
                                              headers=headers)
            if bucket_type == "valid":
                if response.status_code != const.SUCCESS_STATUS:
                    self.log.error(f"POST on {endpoint} request failed.\n"
                                   f"Response code : {response.status_code}")
                    self.log.error(f"Response content: {response.content}")
                    self.log.error(f"Request headers : {response.request.headers}\n"
                                   f"Request body : {response.request.body}")
                    raise CTException(err.CSM_REST_POST_REQUEST_FAILED)

            return response
        except BaseException as error:
            self.log.error("{0} {1}: {2}".format(
                const.EXCEPTION_ERROR,
                RestS3Bucket.create_s3_bucket_for_given_account.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0]) from error

    @RestTestLib.authenticate_and_login
    def list_buckets_under_given_account(self, account_name):
        """
        This function will list down all created buckets under given account_name.
        :param account_name: S3 account name under which we want to create new bucket
        :return: response of list bucket
        """
        self.log.debug("Listing all S3 buckets under {} account".format(account_name))
        endpoint = self.config["s3_bucket_endpoint"]
        self.log.debug("Endpoint for S3 bucket listing is {}".format(endpoint))
        try:
            response = self.restapi.rest_call(
                "get", endpoint=endpoint, headers=self.headers)

        except Exception as error:
            self.log.error("{0} {1}: {2}".format(
                const.EXCEPTION_ERROR,
                RestS3Bucket.list_buckets_under_given_account.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0])
        if response.status_code != const.SUCCESS_STATUS:
            self.log.error(f"GET on {endpoint} request failed.\n"
                           f"Response code : {response.status_code}")
            self.log.error(f"Response content: {response.content}")
            self.log.error(f"Request headers : {response.request.headers}\n"
                           f"Request body : {response.request.body}")
            raise CTException(err.CSM_REST_GET_REQUEST_FAILED,
                              msg="List buckets under given account failed.")
        return response

    @RestTestLib.authenticate_and_login
    def delete_given_s3_bucket(self, bucket_name, account_name):
        """
        This function will delete given s3 bucket.
        :param bucket_name: name of bucket to be deleted
        :param account_name: S3 account name under which we want to create new bucket
        """
        self.log.debug("Deleting given S3 bucket under {} account".format(account_name))
        endpoint = "{}/{}".format(self.config["s3_bucket_endpoint"], bucket_name)
        self.log.debug("Endpoint for S3 bucket deletion is {}".format(endpoint))
        try:
            response = self.restapi.rest_call("delete", endpoint=endpoint, headers=self.headers)
        except Exception as error:
            self.log.error("{0} {1}: {2}".format(
                const.EXCEPTION_ERROR,
                RestS3Bucket.delete_given_s3_bucket.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0])
        if response.status_code != const.SUCCESS_STATUS:
            self.log.error(f"DELETE on {endpoint} request failed.\n"
                           f"Response code : {response.status_code}")
            self.log.error(f"Response content: {response.content}")
            self.log.error(f"Request headers : {response.request.headers}\n"
                           f"Request body : {response.request.body}")
            raise CTException(err.CSM_REST_GET_REQUEST_FAILED, msg="Delete given s3 bucket failed.")


class RestS3BucketPolicy(RestTestLib):
    """RestS3BucketPolicy contains all the Rest Api calls for s3 bucket
    policy operations"""

    def __init__(self, bucketname, ):
        super(RestS3BucketPolicy, self).__init__()
        template_payload = Template(const.BUCKET_POLICY_PAYLOAD)
        payload = template_payload.substitute(
            value=bucketname,
            s3operation='DeleteObject',
            effect='Allow',
            principal='*')
        invalid_payload = template_payload.substitute(value=bucketname,
            s3operation='GetObct', effect='Allow', principal='*')
        update_payload = template_payload.substitute(value=bucketname,
            s3operation='GetObject', effect='Allow', principal='*')
        iam_principal_payload = Template(const.BUCKET_POLICY_PAYLOAD_IAM)
        multi_policy_payload = Template(const.MULTI_BUCKET_POLICY_PAYLOAD)
        self._bucketpolicy_payload = {
            "payload": payload,
            "updated_payload": update_payload,
            "invalid_payload": invalid_payload,
            "custom": iam_principal_payload,
            "multi_policy": multi_policy_payload
        }
        self.bucket_name = bucketname

    @RestTestLib.authenticate_and_login
    def create_bucket_policy(self, operation="default", custom_policy_params=None):
        """
         This function will create new s3 bucket policy
         :param operation: type of operation to pass in payload
         (default : "default")
         possible values ("update_policy","invalid_payload")
         :param custom_policy_params: customised policy parameter passed to payload
         :return: response of create bucket policy
         """
        try:
            if custom_policy_params is None:
                custom_policy_params = {}
            # Building request url
            self.log.debug("Put bucket policy")
            endpoint = self.config["bucket_policy_endpoint"].format(
                self.bucket_name)
            self.log.debug("Endpoint for bucket policy is %s", endpoint)

            # Collecting required payload to be added for request
            if operation == "default":
                user_data = self._bucketpolicy_payload["payload"]
            elif operation == "update_policy":
                user_data = self._bucketpolicy_payload["updated_payload"]
            elif operation == "invalid_payload":
                user_data = self._bucketpolicy_payload["invalid_payload"]
            elif operation == "custom":
                user_data = self._bucketpolicy_payload[operation]
                user_data = user_data.substitute(
                    value=self.bucket_name,
                    s3operation=custom_policy_params['s3operation'],
                    effect=custom_policy_params['effect'],
                    principal=custom_policy_params['principal'])
            elif operation == "multi_policy":
                user_data = self._bucketpolicy_payload[operation]
                user_data = user_data.substitute(
                    value=self.bucket_name,
                    s3operation1=custom_policy_params['s3operation1'],
                    s3operation2=custom_policy_params['s3operation2'],
                    effect=custom_policy_params['effect'],
                    principal=custom_policy_params['principal'])

            self.log.debug("Payload for s3 bucket is %s", user_data)
            self.headers.update(self.config["Login_headers"])
            self.user_data = user_data
            # Fetching api response
            return self.restapi.rest_call(
                "put", endpoint=endpoint, data=user_data, headers=self.headers)

        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3BucketPolicy.create_bucket_policy.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error) from error

    # pylint: disable=too-many-arguments
    def create_and_verify_bucket_policy(
            self,
            expected_status_code=200,
            login_as="s3account_user",
            operation="default",
            custom_policy_params=None,
            validate_expected_response=True):
        """
        This function will create and verify that new bucket policy applied
        :param expected_status_code: expected status code to be verify
        :param login_as: The type of user you desire to login
        (default : s3account_user)
        possible values (csm_admin_user, s3account_user, csm_user_manage,
        csm_user_monitor)
        :param operation: type of operation to pass in payload
        (default : "default")
         possible values ("update_policy","invalid_payload")
        :param custom_policy_params: customised policy parameter passed to payload
        :param validate_expected_response : validation of expected response
        :return: Success(True)/Failure(False)
        """
        try:
            if custom_policy_params is None:
                custom_policy_params = {}
            response = self.create_bucket_policy(
                operation=operation, custom_policy_params=custom_policy_params,
                login_as=login_as)
            if response.status_code != expected_status_code:
                self.log.error(
                    "Response is not 200, Response=%s",
                        response.status_code)
                return False
            response = response.json()

            # Validating response value
            if validate_expected_response:
                exp_response = {
                    "message": "Bucket Policy Updated Successfully."}
                if response != exp_response:
                    self.log.error("Values does not match ")
                    return False
            return True

        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3BucketPolicy.create_and_verify_bucket_policy.__name__,
                error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                error) from error

    @RestTestLib.authenticate_and_login
    def get_bucket_policy(self, bucket_name=None, login_as="s3account_user"):
        """
         This function will get s3 bucket policy
         :param bucket_type: type of bucket required
         :param login_as: The type of user you desire to login
         (default : s3account_user)
         possible values (csm_admin_user, s3account_user, csm_user_manage,
         csm_user_monitor)
         :return: response of get bucket policy
         """
        try:
            # Building request url
            self.log.debug("Get bucket policy")
            if bucket_name:
                endpoint = self.config["bucket_policy_endpoint"].format(
                    bucket_name)
            else:
                endpoint = self.config["bucket_policy_endpoint"].format(
                    self.bucket_name)
            self.log.debug("Endpoint for bucket policy is %s", endpoint)

            self.headers.update(self.config["Login_headers"])

            # Fetching api response
            return self.restapi.rest_call(
                "get", endpoint=endpoint, headers=self.headers)

        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3BucketPolicy.get_bucket_policy.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error

    def get_and_verify_bucket_policy(self, validate_expected_response=True,
                                     expected_status_code=200,
                                     login_as="s3account_user",
                                     invalid_bucket=False):
        """
        This function will get and verify that bucket policy applied or not
        :param validate_expected_response : validation of expected response
        :param expected_status_code: expected status code to be verify
        :param login_as: The type of user you desire to login(default : s3account_user)
        possible values (csm_admin_user, s3account_user, csm_user_manage,
        csm_user_monitor)
        :param invalid_bucket: type of bucket to pass in payload (default : False)
        possible value (True)
        :return: Success(True)/Failure(False)
        """
        try:
            self.log.debug("Get and verify bucket policy")
            if invalid_bucket:
                invalid_bucket_name = ''.join(('buk', str(int(time.time()))))
                response = self.get_bucket_policy(
                    bucket_name=invalid_bucket_name, login_as=login_as)
            else:
                response = self.get_bucket_policy(login_as=login_as)
            if response.status_code != expected_status_code:
                self.log.error(
                    "Response is not 200, Response=%s",
                        response.status_code)
                return False
            if (validate_expected_response) and (
                    json.loads(self.user_data) != response.json()):
                self.log.error(
                    "Values does not match : response=%s",
                        response.json())
                return False
            return True

        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3BucketPolicy.get_and_verify_bucket_policy.__name__,
                error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                error) from error

    @RestTestLib.authenticate_and_login
    def delete_bucket_policy(self, login_as="s3account_user"):
        """
         This function will delete s3 bucket policy
         :param login_as: The type of user you desire to login
         (default : s3account_user)
         possible values (csm_admin_user, s3account_user, csm_user_manage,
         csm_user_monitor)
         :return: response of delete bucket policy
         """
        try:
            # Building request url
            self.log.debug("Delete bucket policy")
            endpoint = self.config["bucket_policy_endpoint"].format(
                self.bucket_name)
            self.log.debug("Endpoint for bucket policy is %s", endpoint)

            self.headers.update(self.config["Login_headers"])

            # Fetching api response
            return self.restapi.rest_call(
                "delete", endpoint=endpoint, headers=self.headers)

        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3BucketPolicy.delete_bucket_policy.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error

    def delete_and_verify_bucket_policy(self, expected_status_code=200,
                                        login_as="s3account_user"):
        """
        This function will delete and verify that bucket policy deleted or not
        :param expected_status_code: expected status code to be verify
        :param login_as: The type of user you desire to login
        (default : s3account_user)
        possible values (csm_admin_user, s3account_user, csm_user_manage,
        csm_user_monitor)
        :return: Success(True)/Failure(False)
        """
        try:
            self.log.debug("Delete and verify bucket policy")
            response = self.delete_bucket_policy(login_as=login_as)
            if response.status_code != expected_status_code:
                self.log.error(
                    "Response is not 200, Response=%s",
                        response.status_code)
                return False
            return True

        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestS3BucketPolicy.delete_and_verify_bucket_policy.__name__,
                error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                error) from error

    @RestTestLib.authenticate_and_login
    def create_bucket_policy_under_given_account(self, account_name):
        """
        This function will create new s3 bucket policy under given account_name.
        :param account_name: S3 account name under which we want to create new bucket
        """
        self.log.debug("Creating bucket policy under {} account".format(account_name))
        endpoint = self.config["bucket_policy_endpoint"].format(self.bucket_name)
        self.log.debug("Endpoint for bucket policy creation is {}".format(endpoint))
        user_data = self._bucketpolicy_payload["payload"]
        try:
            response = self.restapi.rest_call("put", endpoint=endpoint,
                                              data=user_data, headers=self.headers)
        except Exception as error:
            self.log.error("{0} {1}: {2}".format(
                const.EXCEPTION_ERROR,
                RestS3BucketPolicy.create_bucket_policy_under_given_account.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0])
        if response.status_code != const.SUCCESS_STATUS:
            self.log.error(f"PUT on {endpoint} request failed.\n"
                           f"Response code : {response.status_code}")
            self.log.error(f"Response content: {response.content}")
            self.log.error(f"Request headers : {response.request.headers}\n"
                           f"Request body : {response.request.body}")
            raise CTException(err.CSM_REST_PUT_REQUEST_FAILED, msg="Create bucket policy failed.")

    @RestTestLib.authenticate_and_login
    def get_bucket_policy_under_given_account(self, account_name):
        """
        This function will get s3 bucket policy under given account_name.
        :param account_name: S3 account name under which we want to create new bucket
        :return: response of get bucket policy
        """
        self.log.debug("Getting bucket policy under {} account".format(account_name))
        endpoint = self.config["bucket_policy_endpoint"].format(self.bucket_name)
        self.log.debug("Endpoint for bucket policy get is {}".format(endpoint))
        try:
            response = self.restapi.rest_call("get", endpoint=endpoint, headers=self.headers)
            if response.status_code != const.SUCCESS_STATUS:
                self.log.error(f"GET on {endpoint} request failed.\n"
                               f"Response code : {response.status_code}")
                self.log.error(f"Response content: {response.content}")
                self.log.error(f"Request headers : {response.request.headers}\n"
                               f"Request body : {response.request.body}")
                raise CTException(err.CSM_REST_GET_REQUEST_FAILED)
            return response
        except Exception as error:
            self.log.error("{0} {1}: {2}".format(
                const.EXCEPTION_ERROR,
                RestS3BucketPolicy.get_bucket_policy_under_given_account.__name__,
                error))
            raise CTException(err.CSM_REST_AUTHENTICATION_ERROR, error.args[0]) from error

    @RestTestLib.authenticate_and_login
    def delete_bucket_policy_under_given_name(self, account_name):
        """
        This function will delete s3 bucket policy under given account_name.
        :param account_name: S3 account name under which we want to create new bucket
        :return: response of delete bucket policy
        """
        self.log.debug("Deleting bucket policy under {} account".format(account_name))
        endpoint = self.config["bucket_policy_endpoint"].format(self.bucket_name)
        self.log.debug("Endpoint for bucket policy deletion is {}".format(endpoint))
        try:
            response = self.restapi.rest_call("delete", endpoint=endpoint, headers=self.headers)
        except Exception as error:
            self.log.error("{0} {1}: {2}".format(
                const.EXCEPTION_ERROR,
                RestS3BucketPolicy.delete_bucket_policy_under_given_name.__name__,
                error))
            raise CTException(err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])
        if response.status_code != const.SUCCESS_STATUS:
            self.log.error(f"DELETE on {endpoint} request failed.\n"
                           f"Response code : {response.status_code}")
            self.log.error(f"Response content: {response.content}")
            self.log.error(f"Request headers : {response.request.headers}\n"
                           f"Request body : {response.request.body}")
            raise CTException(err.CSM_REST_DELETE_REQUEST_FAILED, msg="Delete bucket policy failed")
        return response
