"""Test library for audit logs."""
import eos_test.common.eos_errors as err
from ctp.common.ctpexception import CTPException
from eos_test.csm.rest.csm_rest_test_lib import RestTestLib as Base


class RestAuditLogs(Base):
    """RestAuditLogs contains all the Rest Api calls for audit logs operations"""
    def __init__(self, component_csm, component_s3):
        super(RestAuditLogs, self).__init__()
        self.component_csm = "csm"
        self.component_s3 = "s3"
        self.invalid_component = "invalid"

    @Base.authenticate_and_login
    def audit_logs_csm_show(self, params, invalid_component=False):
        try:
            # Building request url
            self._log.info("Show audit logs for csm")
            if not invalid_component:
                endpoint = self.config["audit_logs_show_endpoint"].format(self.component_csm)
            else:
                endpoint = self.config["audit_logs_show_endpoint"].format(self.invalid_component)
            self._log.info("Endpoint for csm show audit logs is {}".format(endpoint))

            self.headers.update(self.config["Login_headers"])
            return self.restapi.rest_call("get", endpoint=endpoint, headers=self.headers, params=params)
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestAuditLogs.audit_logs_csm_show.__name__,
                error))
            raise CTPException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0])

    def verify_audit_logs_csm_show(self,
                                   params,
                                   expected_status_code=200,
                                   login_as="csm_admin_user",
                                   validate_expected_response=True,
                                   invalid_component=False
                                   ):
        try:
            response = self.audit_logs_csm_show(login_as=login_as, params=params, invalid_component=invalid_component)
            if response.status_code != expected_status_code:
                self._log.error(
                    "Response is not 200, Response={}".format(
                        response.status_code))
                return False

            # Validating response value
            if validate_expected_response:
                response = response.json()
                pattern1 = ('csm_agent_audit', 'audit:', 'User:', 'Remote_IP:', 'Url:', 'Method:GET', 'User-Agent:', 'RC:')
                pattern2 = ('csm_agent_audit', 'audit:', 'Remote_IP:', 'Url:', 'Method:POST', 'User-Agent:', 'RC:')
                pattern3 = ('csm_agent_audit', 'audit:', 'Remote_IP:', 'Url:', 'Method:GET', 'User-Agent:', 'RC:')
                for element in response:
                    if 'Method:GET' in element:
                        retval = True
                        for i in pattern1:
                            if i not in element:
                                self._log.error("Values does not match for get {}".format(element))
                                retval = False
                                break
                        if not retval:
                            for i in pattern3:
                                if i not in element:
                                    self._log.error("Values does not match for get {}".format(element))
                                    return False

                    elif 'Method:POST' in element:
                        for i in pattern2:
                            if i not in element:
                                self._log.error("Values does not match for post {}".format(element))
                                return False
            return True

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestAuditLogs.verify_audit_logs_csm_show.__name__,
                error))
            raise CTPException(
                err.CSM_REST_VERIFICATION_FAILED,
                error.args[0])

    @Base.authenticate_and_login
    def audit_logs_csm_download(self, params, invalid_component=False):
        try:
            # Building request url
            self._log.info("Download audit logs for csm")
            if not invalid_component:
                endpoint = self.config["audit_logs_download_endpoint"].format(self.component_csm)
            else:
                endpoint = self.config["audit_logs_download_endpoint"].format(self.invalid_component)
            self._log.info("Endpoint for csm download audit logs is {}".format(endpoint))

            self.headers.update(self.config["Login_headers"])
            return self.restapi.rest_call("get", endpoint=endpoint, headers=self.headers, params=params)
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestAuditLogs.audit_logs_csm_download.__name__,
                error))
            raise CTPException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0])

    def verify_audit_logs_csm_download(self,
                                       params,
                                       expected_status_code=200,
                                       login_as="csm_admin_user",
                                       validate_expected_response=True,
                                       invalid_component=False,
                                       response_type=None
                                       ):
        try:
            response = self.audit_logs_csm_download(login_as=login_as, params=params, invalid_component=invalid_component)
            if response.status_code != expected_status_code:
                self._log.error(
                    "Response is not 200, Response={}".format(
                        response.status_code))
                return False

            # Validating response value
            if validate_expected_response:
                if response_type:
                    return isinstance(response.text, response_type)
                self.response = response.json()
                exp_response = {"Message": "Audit logs for csm downloaded Successfully."}
                if self.response != exp_response:
                    self._log.error("Values does not match ")
                    return False
            return True

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestAuditLogs.verify_audit_logs_csm_download.__name__,
                error))
            raise CTPException(
                err.CSM_REST_VERIFICATION_FAILED,
                error.args[0])

    @Base.authenticate_and_login
    def audit_logs_s3_show(self, params):
        try:
            # Building request url
            self._log.info("Show audit logs for s3")
            endpoint = self.config["audit_logs_show_endpoint"].format(self.component_s3)
            self._log.info("Endpoint for s3 show audit logs is {}".format(endpoint))

            self.headers.update(self.config["Login_headers"])
            return self.restapi.rest_call("get", endpoint=endpoint, headers=self.headers, params=params)
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestAuditLogs.audit_logs_s3_show.__name__,
                error))
            raise CTPException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0])

    def verify_audit_logs_s3_show(self,
                                   params,
                                   expected_status_code=200,
                                   login_as="csm_admin_user",
                                   validate_expected_response=True,

                                   ):
        try:
            response = self.audit_logs_s3_show(login_as=login_as, params=params)
            if response.status_code != expected_status_code:
                self._log.error(
                    "Response is not 200, Response={}".format(
                        response.status_code))
                return False

            # Validating response value
            if validate_expected_response:
                self.response = response.json()
                exp_response = {"Message": "Audit logs for s3 showed Successfully."}
                if self.response != exp_response:
                    self._log.error("Values does not match ")
                    return False
            return True

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestAuditLogs.verify_audit_logs_s3_show.__name__,
                error))
            raise CTPException(
                err.CSM_REST_VERIFICATION_FAILED,
                error.args[0])

    @Base.authenticate_and_login
    def audit_logs_s3_download(self, params):
        try:
            # Building request url
            self._log.info("Download audit logs for s3")
            endpoint = self.config["audit_logs_download_endpoint"].format(self.component_s3)
            self._log.info("Endpoint for s3 download audit logs is {}".format(endpoint))

            self.headers.update(self.config["Login_headers"])
            return self.restapi.rest_call("get", endpoint=endpoint, headers=self.headers, params = params)
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestAuditLogs.audit_logs_s3_download.__name__,
                error))
            raise CTPException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0])

    def verify_audit_logs_s3_download(self,
                                    params,
                                    expected_status_code=200,
                                    login_as="csm_admin_user",
                                    validate_expected_response=True,
                                    response_type = None,
                                    ):
        try:
            response = self.audit_logs_s3_download(login_as=login_as, params=params)
            if response.status_code != expected_status_code:
                self._log.error(
                    "Response is not 200, Response={}".format(
                        response.status_code))
                return False

            # Validating response value
            if validate_expected_response:
                if response_type:
                    return isinstance(response.text, response_type)
                self.response = response.json()
                exp_response = {"Message": "Audit logs for s3 downloaded Successfully."}
                if self.response != exp_response:
                    self._log.error("Values does not match ")
                    return False
            return True

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestAuditLogs.verify_audit_logs_s3_download.__name__,
                error))
            raise CTPException(
                err.CSM_REST_VERIFICATION_FAILED,
                error.args[0])
