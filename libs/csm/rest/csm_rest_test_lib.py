""" REST API Alert operation Library. """
import logging
from string import Template
from jsonschema import validate
import commons.errorcodes as err
from commons.constants import Rest as const
from commons.utils import config_utils
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_core_lib import RestClient




class RestTestLib:
    """
        This is the class for common test library
    """

    def __init__(self):
        self.csm_conf = config_utils.read_yaml("config/csm/csm_config.yaml")[1]
        self.config = self.csm_conf["Restcall"]
        self._log = logging.getLogger(__name__)
        self.restapi = RestClient(self.csm_conf["Restcall"])
        self.user_type = ("valid", "duplicate", "invalid", "missing")
        self.success_response = const.SUCCESS_STATUS
        self.bad_request_response = const.BAD_REQUEST
        self.conflict_response = const.CONFLICT
        self.forbidden = const.FORBIDDEN
        self.method_not_found = const.METHOD_NOT_FOUND
        self.default_s3user_name = self.config["s3account_user"]["username"]
        self.default_csm_user_monitor = self.config["csm_user_monitor"]["username"]
        self.default_csm_user_manage = self.config["csm_user_manage"]["username"]
        self.exception_error = const.EXCEPTION_ERROR
        self.success_response_post = const.SUCCESS_STATUS_FOR_POST

    def rest_login(self, login_as):
        """
        This function will request for login
        login_as str: The type of user you desire to login
        object : In case complete response is required
        """
        try:
            # Building response
            endpoint = self.config["rest_login_endpoint"]
            headers = self.config["Login_headers"]
            self._log.info(f"endpoint {endpoint}")
            # payload = self.config[login_as] # showing some error in Cortx-1.0.0-rc3
            payload = Template(const.LOGIN_PAYLOAD).substitute(
                **self.config[login_as])

            # Fetch and verify response
            response = self.restapi.rest_call(
                "post", endpoint, headers=headers, data=payload, save_json=False)
            self._log.info(f"response : {response}")

            return response
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestTestLib.rest_login.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])

    def custom_rest_login(self, username, password,
                           username_key="username", password_key="password"):
        """
        This function tests the invalid login scenarios
        :param str username: username
        :param str password: password
        :param str username_key: key word for json load for username
        :param str password_key: key word for json load for password
        :return [object]: response
        """
        try:
            # Building response
            endpoint = self.config["rest_login_endpoint"]
            headers = self.config["Login_headers"]
            self._log.info(f"endpoint {endpoint}")
            payload = "{{\"{}\":\"{}\",\"{}\":\"{}\"}}".format(
                username_key, username, password_key, password)

            # Fetch and verify response
            response = self.restapi.rest_call(
                "post", endpoint, headers=headers, data=payload, save_json=False)
            self._log.info(f"response : {response}")

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestTestLib.custom_rest_login.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])
        return response

    def authenticate_and_login(func):
        """
        :type: Decorator
        :functionality: Authorize the user before any rest calls
        """
        def create_authenticate_header(self, *args, **kwargs):
            """
            This function will fetch the login token and create the authentication header
            :param self: reference of class object
            :param args: arguments of the executable function
            :param kwargs: keyword arguments of the executable function
            :keyword login_as : type of user making the REST call (string)
            :keyword authorized : to verify unauthorized scenarios (boolean)
            :return: function executables
            """
            self.headers = {}  # Initiate headers
            self._log.info(
                "user is getting authorized for REST operations ...")

            # Checking the type of login user
            login_type = kwargs.pop(
                "login_as") if "login_as" in kwargs else "csm_admin_user"

            # Checking the requirements to authorize
            authorized = kwargs.pop(
                "authorized") if "authorized" in kwargs else True

            # Fetching the login response
            self._log.info("user will be logged in as {}".format(login_type))
            response = self.rest_login(login_as=login_type)

            if authorized and response.status_code == const.SUCCESS_STATUS:
                self.headers = {
                    'Authorization': response.headers['Authorization']}

            return func(self, *args, **kwargs)
        return create_authenticate_header

    def update_csm_config_for_user(self, user_type, username, password):
        """
         This function will update user config in run time
        :param user_type: new user type
        :param username: user name of new user
        :param password: password of new user
        :return: Boolean value for successful creation
        """
        try:
            # Updating configurations
            self.config.update({
                user_type: {"username": username, "password": password}
            })

            # Verify successfully added
            return user_type in self.config
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestTestLib.update_csm_config_for_user.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def verify_json_response(self, actual_result, expect_result, match_exact=False):
        """
        This function will verify the json response with actual response
        :param actual_result: actual json response from REST call
        :param expect_result: the json response to be matched
        :param match_exact: to match actual and expect result to be exact
        :return: Success(True)/Failure(False)
        """
        try:
            # Matching exact values
            if match_exact:
                self._log.info("Matching exact values")
                return actual_result == expect_result

            # Check for common keys between actual value and expect value
            if actual_result.keys().isdisjoint(expect_result):
                self._log.info(
                    "No common keys between actual value and expect value")
                return False

            return all(actual_result[key] == value for key, value in expect_result.items())
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestTestLib.verify_json_response.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def verify_json_schema(self, instance, *schemas):
        """
        Verify the schema for the given instance of the response
        exception is raised if the schema doesn't match 
        which can be handled by calling function
        :param instance: json log instance which needs to be verified.
        :param schemas: json schema for verification
        """

        for schema in schemas:
            validate(instance=instance, schema=schema)
