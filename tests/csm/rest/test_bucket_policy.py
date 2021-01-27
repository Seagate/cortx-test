import sys
import logging
import pytest
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_bucket import RestS3BucketPolicy
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.csm.csm_setup import CSMConfigsCheck

class TestBucketPolicy():
    """S3 Bucket Policy Testsuite
    """
    @classmethod
    def setup_class(cls):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.a
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups")
        cls.config = CSMConfigsCheck()
        setup_ready = cls.config.check_predefined_s3account_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_s3
        assert setup_ready

    def setup_method(self, method):
        self.s3_buckets = RestS3Bucket()
        self.log.info("Creating bucket for test")
        response = self.s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="s3account_user")
        self.bucket_name = response.json()['bucket_name']
        print("##### bucket name {} #####".format(self.bucket_name))
        self.bucket_policy = RestS3BucketPolicy(self.bucket_name)
        self.rest_iam_user = RestIamUser()
        self.created_iam_users = set()
        self.log.info("Ended test setups")

    def teardown_method(self, method):
        self.log.info("Teardown started")
        self.s3_buckets.delete_s3_bucket(
            bucket_name=self.bucket_name,
            login_as="s3account_user")
        for user in self.created_iam_users:
            self.rest_iam_user.delete_iam_user(login_as="s3account_user", user=user)
        self.log.info("Teardown ended")

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10783')
    def test_4212(self):
        """Test that s3 user can add bucket policy
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.bucket_policy.create_and_verify_bucket_policy()
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10784')
    def test_4213(self):
        """Test that s3 user can update bucket policy
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.bucket_policy.create_and_verify_bucket_policy()
        assert self.bucket_policy.create_and_verify_bucket_policy(operation='update_policy')
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10785')
    def test_4214(self):
        """Test that error is retuned when s3 user sends PUT request with invalid json
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.bucket_policy.create_and_verify_bucket_policy(expected_status_code=400,
                                                                           operation="invalid_payload",
                                                                           validate_expected_response=False)
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10779')
    def test_4215(self):
        """test that s3 user can GET current bucket policy
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.bucket_policy.create_and_verify_bucket_policy(
                login_as="s3account_user")
        assert self.bucket_policy.get_and_verify_bucket_policy()
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10788')
    def test_4216(self):
        """Test that error code is returned when s3 user send GET request on bucket when no bucket policy exist on it
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.bucket_policy.get_and_verify_bucket_policy(expected_status_code=404,
                                                                        validate_expected_response=False)
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10781')
    def test_4217(self):
        """Test that error is returned when s3 user send GET request on incorrect/invalid bucket
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.bucket_policy.create_and_verify_bucket_policy()
        assert self.bucket_policy.get_and_verify_bucket_policy(
                validate_expected_response=False,
                expected_status_code=404,
                invalid_bucket=True)
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10780')
    def test_4218(self):
        """Test that s3 user can delete bucket policy
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.bucket_policy.create_and_verify_bucket_policy()
        assert self.bucket_policy.delete_and_verify_bucket_policy()
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10786')
    def test_4219(self):
        """Test that error is returned when s3 user try delete bucket policy which doesn't exist
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        assert self.bucket_policy.delete_and_verify_bucket_policy(expected_status_code=404)
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10792')
    def test_4220(self):
        """test that s3 user can add bucket policy to allow some bucket related actions to specific user
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        assert status, response
        user_id = response['user_id']
        self.created_iam_users.add(response['user_name'])
        policy_params = {'s3operation': 'GetObject',
                         'effect': 'Allow',
                         'principal': user_id}
        assert self.bucket_policy.create_and_verify_bucket_policy(
                operation='custom', custom_policy_params=policy_params,
                validate_expected_response=False)
        assert self.bucket_policy.get_and_verify_bucket_policy()
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10794')
    def test_4221(self):
        """test that s3 user can add bucket policy to allow many(more than one) bucket related actions
        to many(more than one) users
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        assert status, response
        user_id = response['user_id']
        self.created_iam_users.add(response['user_name'])
        policy_params = {'s3operation1': 'GetObject',
                         's3operation2': 'DeleteObject',
                         'effect': 'Allow',
                         'principal': user_id
                        }
        assert self.bucket_policy.create_and_verify_bucket_policy(
                operation='multi_policy', custom_policy_params=policy_params)
        assert self.bucket_policy.get_and_verify_bucket_policy()
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10793')
    def test_4222(self):
        """test that s3 user can add bucket policy to deny all bucket related actions to specific user
         :avocado: tags=bucket_policy
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        assert status, response
        user_id = response['user_id']
        self.created_iam_users.add(response['user_name'])
        policy_params = {'s3operation': 'GetObject',
                         'effect': 'Deny',
                         'principal': user_id}
        assert self.bucket_policy.create_and_verify_bucket_policy(
                operation='custom', custom_policy_params=policy_params)
        assert self.bucket_policy.get_and_verify_bucket_policy()
        self.log.info("##### Test ended -  {} #####".format(test_case_name))
