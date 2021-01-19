import sys
import pytest
import logging
from libs.csm.rest.csm_rest_bucket import RestS3Bucket 
from libs.csm.rest.csm_rest_s3user import RestS3user
#from eos_test.csm.csm_setup import CSMConfigsCheck
from commons.utils import config_utils
from commons.constants import Rest as const
from commons.utils import assert_utils

class TestS3Bucket():
    @classmethod
    def setup_class(self):
        """ This is method is for test suite set-up """
        self.log = logging.getLogger(__name__)
        self.log.info("Initializing test setups ......")
        #self.config = CSMConfigsCheck()
        #setup_ready = self.config.check_predefined_s3account_present()
        #if not setup_ready:
        #    setup_ready = self.config.setup_csm_s3
        #assert setup_ready)
        self.s3_buckets = RestS3Bucket()
        self.s3_account = RestS3user()
        self.log.info("Initiating Rest Client for Alert ...")
        self.csm_conf = config_utils.read_yaml(
            "config/csm/test_rest_s3_bucket.yaml")[1]

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_573(self):
        """Initiating the test case for the verifying response of create bucket rest
        :avocado: tags=create_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.s3_buckets.create_and_verify_new_bucket(
            self.s3_buckets.success_response)

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_575(self):
        """Initiating the test case for the verifying response of create bucket rest with bucket name less than three
        :avocado: tags=create_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.s3_buckets.create_and_verify_new_bucket(
            self.s3_buckets.bad_request_response, bucket_type="bucket_name_less_than_three_char")

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_576(self):
        """Initiating the test case for the verifying response of create bucket rest with bucket name more than 63
        :avocado: tags=create_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.s3_buckets.create_and_verify_new_bucket(
            self.s3_buckets.bad_request_response, bucket_type="bucket_name_more_than_63_char")

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_577(self):
        """Initiating the test case for the verifying response of create bucket rest invalid initial letter of bucket
        :avocado: tags=create_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.log.info("checking for bucket name start_with_underscore")
        start_with_underscore = self.s3_buckets.create_and_verify_new_bucket(
            self.s3_buckets.bad_request_response, bucket_type="start_with_underscore")
        self.log.info("The status for bucket name start_with_underscore is {}".format(
            start_with_underscore))
        start_with_uppercase = self.s3_buckets.create_and_verify_new_bucket(
            self.s3_buckets.bad_request_response, bucket_type="start_with_uppercase")
        self.log.info("The status for bucket name start_with_uppercase is {}".format(
            start_with_uppercase))
        assert start_with_uppercase and start_with_underscore

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_579(self):
        """Initiating the test case for the verifying response of create bucket rest for ip address as bucket name
        :avocado: tags=create_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.s3_buckets.create_and_verify_new_bucket(
            self.s3_buckets.bad_request_response, bucket_type="ip_address")

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_580(self):
        """Initiating the test case for the verifying response of create bucket rest with unauthorized user login
        :avocado: tags=create_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        response = self.s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="csm_admin_user")
        assert self.s3_buckets.forbidden == response.status_code

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_581(self):
        """Initiating the test case for the verifying response of create bucket rest with duplicate user
        :avocado: tags=create_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.s3_buckets.create_and_verify_new_bucket(
            self.s3_buckets.conflict_response, bucket_type="duplicate")

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_589(self):
        """Initiating the test case for the verifying response of create bucket rest with invalid data
        :avocado: tags=create_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.s3_buckets.create_and_verify_new_bucket(
            self.s3_buckets.bad_request_response, bucket_type="invalid")

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_591(self):
        """Initiating the test case for the verifying response of list bucket rest
        :avocado: tags=get_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="s3account_user")
        assert self.s3_buckets.list_and_verify_bucket()
    
    @pytest.mark.test(test_id=5011, tag='csm')
    def test_593(self):
        """Initiating the test case for the verifying response of bucket rest for newly created s3 account
        :avocado: tags=get_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.s3_account.create_s3_account(save_new_user=True)
        self.s3_buckets.list_and_verify_bucket(
            expect_no_user=True, login_as="new_s3_account_user")

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_594(self):
        """Initiating the test case for the verifying response of list bucket rest with unauthorized user login
        :avocado: tags=get_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        response = self.s3_buckets.list_all_created_buckets(
            login_as="csm_admin_user")
        assert self.s3_buckets.forbidden == response.status_code

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_596(self):
        """Initiating the test case for the verifying response of delete bucket rest
        :avocado: tags=delete_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.s3_buckets.delete_and_verify_new_bucket(
            self.s3_buckets.success_response)

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_599(self):
        """Initiating the test case for the verifying response of list bucket rest with unauthorized user login
        :avocado: tags=get_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        response = self.s3_buckets.delete_s3_bucket(
            bucket_name="any_name", login_as="csm_admin_user")
        assert self.s3_buckets.forbidden == response.status_code

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_597(self):
        """Initiating the test case for the verifying response of delete bucket that does not exist
        :avocado: tags=delete_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.s3_buckets.delete_and_verify_new_bucket(
            self.s3_buckets.method_not_found, bucket_type="does-not-exist")

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_601(self):
        """Initiating the test case for the verifying response of delete bucket rest with no bucket name
        :avocado: tags=delete_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        response = self.s3_buckets.delete_s3_bucket(
            bucket_name="", login_as="s3account_user")
        assert self.s3_buckets.method_not_found == response.status_code

    @pytest.mark.test(test_id=5011, tag='csm')
    def test_578(self):
        """Initiating the test to test RESP API to create bucket with bucketname having special or alphanumeric character
        :avocado: tags= rest_s3_bucket_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        bucketname = self.csm_conf["test_578"]["bucket_name"]
        resp_msg = self.csm_conf["test_578"]["response_msg"]

        self.log.info(
            "Step 1: Verifying creating bucket with bucket name containing special characters")
        response = self.s3_buckets.create_invalid_s3_bucket(
            bucket_name=bucketname[0], login_as="s3account_user")

        self.log.info(response.json())

        self.log.info("Verifying the status code {} and response returned {}".format(
            response.status_code, response.json()))
        assert_utils.assert_equals(response.status_code,
                         self.s3_buckets.bad_request_response)
        assert_utils.assert_equals(response.json(),
                         resp_msg)

        self.log.info(
            "Step 1: Verified creating bucket with bucket name containing special characters")

        self.log.info(
            "Step 2: Verifying creating bucket with bucket name containing alphanumeric characters")
        response = self.s3_buckets.create_invalid_s3_bucket(
            bucket_name=bucketname[1], login_as="s3account_user")

        self.log.info("Verifying the status code {} and response returned {}".format(
            response.status_code, response.json()))
        assert_utils.assert_equals(response.status_code,
                         self.s3_buckets.bad_request_response)
        assert_utils.assert_equals(response.json(),
                         resp_msg)

        self.log.info(
            "Step 1: Verified creating bucket with bucket name containing alphanumeric characters")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))
