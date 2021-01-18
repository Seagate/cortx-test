
import logging
logging.basicConfig(level=logging.DEBUG) 
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
csm_user = RestCsmUser()
csm_user.create_payload_for_new_csm_user("valid", "manage")
csm_user.create_csm_user()
csm_user.create_and_verify_csm_user_creation(user_type="valid", user_role="manage", expect_status_code=201)
actual_resp = csm_user.list_csm_users(expect_status_code=200, return_actual_response=True)
csm_user.verify_list_csm_users(actual_resp)
csm_user.list_actual_num_of_csm_users()
csm_user.verify_csm_user_list_valid_params()
csm_user.verify_list_csm_users_unauthorised_access_failure()
csm_user.list_csm_users_empty_param()
csm_user.list_csm_single_user()
csm_user.verify_modify_csm_user()
csm_user.revert_csm_user_password()
csm_user.verify_user_exits()
csm_user.delete_csm_user()