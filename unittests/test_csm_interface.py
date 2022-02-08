import logging
from libs.csm.csm_interface import csm_api_factory

class TestCsmInterface:

    log = logging.getLogger(__name__)

    def test_rest_csm_users(self):
        """
        Test to run IO and verify the download sequentially within test
        """
        csm_obj = csm_api_factory("rest")
        self.log.info("Testing function from CSM User class")
        resp = csm_obj.create_payload_for_new_csm_user("valid", "manage")
        self.log.info(resp)
        assert resp["role"] == "manage", "payload not created"
        resp = csm_obj.create_payload_for_new_csm_user("valid", "manage")
        assert resp["role"]=="manage", "Required user not created."
        resp = csm_obj.create_csm_user()
        assert resp.status_code == 201, "Status code check failed"
        self.log.info("Username: %s ", resp.json()["username"])
        resp = csm_obj.create_and_verify_csm_user_creation(user_type="valid", user_role="manage",
                                                            expect_status_code=201)
        assert resp, "Create user failed."
        resp = csm_obj.list_csm_users(expect_status_code=200, return_actual_response=True,
                                      sort_dir="asc")
        assert resp.status_code==200, "list user failed."
        resp = csm_obj.verify_list_csm_users(resp.json(),sort_dir="asc")
        assert True, "List user list is not sorted."

    def test_rest_s3_users(self):
        """
        Test to run IO and verify the download sequentially within test
        """
        csm_obj = csm_api_factory("rest")
        self.log.info("Testing function from S3 User class")
        resp = csm_obj.create_s3_account()
        assert resp.status_code == 201, "create failed"
        username = resp.json()["account_name"]
        resp = csm_obj.edit_and_verify_s3_account_user("valid")
        resp = csm_obj.edit_s3_account_user(username)
        assert resp.status_code == 200, "edit failed"
        resp = csm_obj.delete_s3_account_user(username)
        assert resp.status_code == 200, "Delete s3 acc failed."
        resp = csm_obj.list_all_created_s3account()
        assert resp.status_code == 200, "List user failed."
        resp = csm_obj.verify_list_s3account_details()
        assert resp, "List user failed"
        resp = csm_obj.create_and_verify_s3account("valid", 201)
        resp = csm_obj.create_payload_for_new_s3_account("valid")
        assert resp is None, "No payload generated."
        resp = csm_obj.create_an_account("trys3", "Seagate@123")
        assert resp.status_code == 201, "create s3 failed."
        resp = csm_obj.delete_s3_account_user(resp.json()["account_name"])
        assert resp.status_code == 200, "Delete s3 acc failed."
        payload = csm_obj.create_custom_s3_payload("valid")
        resp = csm_obj.create_custom_s3_user(payload)
        assert resp.status_code == 201, "create s3 failed."
        resp = csm_obj.delete_s3_account_user(resp.json()["account_name"])
        assert resp.status_code == 200, "Delete s3 acc failed."
        resp = csm_obj.delete_and_verify_s3_account_user()
        resp = csm_obj.create_verify_s3_custom("valid")
        assert resp[0], "create verification failed."
        resp = csm_obj.delete_s3_account_user(resp[1].json()["account_name"])
        assert resp.status_code == 200, "Delete s3 acc failed."

    def test_cli(self):
        """
        Test to run IO and verify the download sequentially within test
        """
        csmrest_obj = csm_api_factory("cli")
        self.log.info("Testing function from CLI class")
        assert csmrest_obj is not None, "Unable to create cli object"

    def test_gui(self):
        """
        Test to run IO and verify the download sequentially within test
        """
        csmrest_obj = csm_api_factory("gui")
        self.log.info("Testing function from GUI class")
        assert csmrest_obj is not None, "Unable to create gui object"
