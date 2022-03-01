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
import logging
import json
logging.basicConfig(level=logging.DEBUG) 
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from commons.constants import Rest as const

if __name__ == '__main__':
    csm_user = RestCsmUser()
    csm_user.create_payload_for_new_csm_user("valid", "manage")
    create_user_resp=csm_user.create_csm_user()
    username = create_user_resp.json()["username"]
    userid = create_user_resp.json()["id"]
    csm_user.create_verify_and_delete_csm_user_creation(
        user_type="valid", user_role="manage", expect_status_code=201)
    actual_resp = csm_user.list_csm_users(
        expect_status_code=200, return_actual_response=True, sort_dir="asc")
    csm_user.verify_list_csm_users(actual_resp.json(),sort_dir="asc")
    #csm_user.verify_list_csm_users(actual_resp.json(),limit=10)
    #csm_user.verify_list_csm_users(actual_resp.json(),offset=10)
    csm_user.list_actual_num_of_csm_users()
    csm_user.verify_csm_user_list_valid_params()
    #csm_user.verify_list_csm_users_unauthorised_access_failure()
    csm_user.list_csm_users_empty_param(
        expect_status_code=400, csm_list_user_param="sort_dir", return_actual_response=True)
    csm_user.list_csm_users_empty_param(
        expect_status_code=400, csm_list_user_param="sort_dir", return_actual_response=False)
    csm_user.list_csm_single_user(
        request_type="get", expect_status_code=200, user="admin", return_actual_response=True)
    csm_user.list_csm_single_user(
        request_type="get", expect_status_code=200, user="admin", return_actual_response=False)

    payload_login = {"username": username, "password": "Testuser@123"}
    csm_user.verify_modify_csm_user(user=username, payload_login=json.dumps(
        payload_login), expect_status_code=200, return_actual_response=True)
    csm_user.revert_csm_user_password(
        username, "Testuser@123", "Testuser@123", return_actual_response=True)
    csm_user.verify_user_exits(username)
    csm_user.delete_csm_user(userid)

    from libs.csm.rest.csm_rest_s3user import RestS3user
    s3_accounts = RestS3user()
