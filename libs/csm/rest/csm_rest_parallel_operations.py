#Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
"""Test library for load testing related operations."""
import os
from commons.utils import config_utils
from commons.constants import HAX_CONTAINER_NAME
from commons.constants import NAMESPACE
from commons.constants import Rest as rest_const
from commons.commands import GET_MAX_USERS
from commons.commands import GET_REQUEST_USAGE
from libs.jmeter.jmeter_integration import JmeterInt
from libs.csm.rest.csm_rest_test_lib import RestTestLib


# pylint: disable-msg=unexpected-keyword-arg
class RestParallelOps(RestTestLib):
    """RestIamUser contains all the Rest API calls for iam user operations"""

    def __init__(self):
        super(RestParallelOps, self).__init__()
        self.jmx_obj = JmeterInt()
        self.counter = 0
        self.created_iam_users = []

    def get_request_usage_limit(self):
        """
        Fetch request usage limit from consul
        """
        self.log.info("Reading capacity from consul from node : %s", self.master)
        data_pods = self.master.get_all_pods_and_ips("data")
        self.log.debug("Data pods on the setup: %s", data_pods)
        data_pod = self.random_gen.choice(list(data_pods.keys()))
        self.log.info("Reading the stats from data pod : %s", data_pod)
        self.log.info("Reading the stats from Container : %s" , HAX_CONTAINER_NAME)
        cmd_suffix = f"-c {HAX_CONTAINER_NAME} -- {GET_REQUEST_USAGE}"
        resp = self.master.send_k8s_cmd(operation="exec", pod=data_pod, namespace=NAMESPACE,
                                     command_suffix=cmd_suffix, decode=True)
        self.log.info("Response : %s", resp)
        resp = int(resp.split(":")[1])
        self.log.info("CSM request usage limit : %s", resp)
        return resp

    def get_max_csm_user_limit(self):
        """
        Fetch request usage limit from consul
        """

        self.log.info("Reading capacity from consul from node : %s", self.master)
        data_pods = self.master.get_all_pods_and_ips("data")
        self.log.debug("Data pods on the setup: %s", data_pods)
        data_pod = self.random_gen.choice(list(data_pods.keys()))
        self.log.info("Reading the stats from data pod : %s", data_pod)
        self.log.info("Reading the stats from Container : %s" , HAX_CONTAINER_NAME)
        cmd_suffix = f"-c {HAX_CONTAINER_NAME} -- {GET_MAX_USERS}"
        resp = self.master.send_k8s_cmd(operation="exec", pod=data_pod, namespace=NAMESPACE,
                                     command_suffix=cmd_suffix, decode=True)
        self.log.info("Response : %s", resp)
        resp = int(resp.split(":")[1])
        self.log.info("CSM request usage limit : %s", resp)
        return resp


    def get_thread_loop(self, users:int, request_limit:int):
        """
        :param request_thread : Request per thread
        :param count: total number of user to be created
        :param request_limit: max number of parallel user which can be send

        returns dictionary which will distribute count based on request_limit and request_thread
        """
        req_loop = {}

        if users < request_limit:
            req_loop = {users : 1}
        else:
            loop1, remain_users = divmod(users, request_limit)
            req_loop = {request_limit : loop1, remain_users : 1}
        self.log.info("User batches : %s", req_loop)
        return req_loop


    def execute_max_user_loop(self, jmx_file:str, users:int, request_limit:int, ops:str):
        """
        Executes jmeter in batches to create max users
        """
        req_loop = self.get_thread_loop(users, request_limit)
        result = True
        for thread, loop in req_loop.items():
            self.log.info("Running jmeter for Thread: %s and loop: %s", thread, loop)
            batch_cnt = thread * loop + self.counter
            if ops == "create":
                self.write_users_to_create_csv(batch_cnt)
            else:
                self.write_users_to_delete_csv(batch_cnt)
            self.counter += batch_cnt
            tmp = self.jmx_obj.run_verify_jmx(jmx_file, threads=thread, rampup=1, loop=loop)
            if tmp:
                self.log.info("%s Users %s", ops, thread * loop)
            else:
                self.log.error("%s failed.", ops)
            result = result and tmp
        self.counter = 0
        return result

    def execute_max_iam_user_loop(self, jmx_file, users, request_limit, ops:str):
        """
        Executes jmeter in batches to create max users
        """
        req_loop = self.get_thread_loop(users, request_limit)
        result = True
        for thread, loop in req_loop.items():
            self.log.info("Running jmeter for Thread: %s and loop: %s", thread, loop)
            batch_cnt = thread * loop + self.counter
            if ops == "create":
                self.write_iam_users_to_create_csv(batch_cnt)
            else:
                self.write_iam_users_to_delete_csv(batch_cnt)
            self.counter += batch_cnt
            tmp = self.jmx_obj.run_verify_jmx(jmx_file, threads=thread, rampup=1, loop=loop)
            if tmp:
                self.log.info("%s Users %s", ops, thread * loop)
            else:
                self.log.error("%s failed.", ops)
            result = result and tmp
        self.counter = 0
        return result

    def create_multi_iam_user_set_quota_delete(self, users:int, existing_user:int=1):
        """
        Create count number of IAM in parallel and set there Quota then Delete using jmeter libs
        :param users: Number of users to be created
        """
        if users is None:
            user_limit = rest_const.MAX_IAM_USERS
            users = user_limit - existing_user
        jmx_file = "CSM_Create_N_IAM_Set_Quota_Delete.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        request_limit = self.get_request_usage_limit()
        result = self.execute_max_iam_user_loop(jmx_file, users, request_limit,
                                                       ops = "create")
        return result

    def create_multi_iam_user_loaded(self, users:int, existing_user:int=1):
        """
        Create count number of IAM in parallel using jmeter libs
        :param users: Number of users to be created
        """
        if users is None:
            user_limit = rest_const.MAX_IAM_USERS
            users = user_limit - existing_user
        jmx_file = "CSM_Create_N_IAM_Users_Loaded.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        request_limit = self.get_request_usage_limit()
        result = self.execute_max_iam_user_loop(jmx_file, users, request_limit,
                                                       ops = "create")
        return result

    def delete_multi_iam_user_loaded(self):
        """
        Delete IAM users in parallel using jmeter libs
        """
        users = len(self.created_iam_users)
        jmx_file = "CSM_Delete_N_IAM_Users_Loaded.jmx"
        self.log.info("Running jmx script: %s", jmx_file)

        request_limit = self.get_request_usage_limit()
        result = self.execute_max_iam_user_loop(jmx_file, users, request_limit,
                                                       ops = "delete")
        return result

    @RestTestLib.authenticate_and_login
    def create_multi_csm_user(self, users:int, existing_user:int=3):
        """
        Create count number of CSM in parallel using jmeter libs
        :param users: Number of users to be created
        """
        if users is None:
            users = self.get_max_csm_user_limit()
        users = users - existing_user

        jmx_file = "CSM_Create_N_CSM_Users.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        request_limit = self.get_request_usage_limit()
        result = self.execute_max_user_loop(jmx_file, users, request_limit, ops = "create")
        return result

    @RestTestLib.authenticate_and_login
    def create_multi_csm_user_with_List_IAM(self, users:int, existing_user:int=3):
        """
        Create count number of CSM in parallel using jmeter libs
        :param users: Number of users to be created
        """
        if users is None:
            users = self.get_max_csm_user_limit()
        users = users - existing_user

        jmx_file = "CSM_Create_N_Monitor_Create_List_N_IAM.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        request_limit = self.get_request_usage_limit()
        result = self.execute_max_user_loop(jmx_file, users, request_limit, ops = "create")
        return result

    @RestTestLib.authenticate_and_login
    def delete_multi_csm_user(self, users:int, existing_user:int=3):
        """
        Create count number of CSM in parallel using jmeter libs
        :param users: Number of users to be created
        """
        if users is None:
            users = self.get_max_csm_user_limit()
        users = users - existing_user
        jmx_file = "CSM_Delete_N_CsmUsers.jmx"
        self.log.info("Running jmx script: %s", jmx_file)

        request_limit = self.get_request_usage_limit()
        result = self.execute_max_user_loop(jmx_file, users, request_limit, ops = "delete")
        return result

    def write_users_to_delete_csv(self, users:int):
        """
        Creates a csv with list of users to be deleted
        """
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["user"]
        for i in range(self.counter, users):
            content.append({fieldnames[0]: f"newmanageuser{i}"})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)

    def write_users_to_create_csv(self, users:int):
        """
        Creates a csv with list of user to be created
        """
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["role", "user", "pswd"]
        for i in range(self.counter, users):
            content.append({fieldnames[0]: "manage",
                        fieldnames[1]: f"newmanageuser{i}",
                        fieldnames[2]: "Seagate@1"})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)

    def write_iam_users_to_create_csv(self, users):
        """
        Creates a csv with list of user to be created
        """
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["uid"]
        i = self.counter
        while i < users:
            uid_suffix = self.random_gen.randrange(9, 9999999)
            if f"newiamuser_{uid_suffix}" not in self.created_iam_users:
                self.created_iam_users.append(f"newiamuser_{uid_suffix}")
                content.append({
                            fieldnames[0]: f"newiamuser_{uid_suffix}",
                            })
                i +=1
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)

    def write_iam_users_to_delete_csv(self, users:int):
        """
        Creates a csv with list of users to be deleted
        """
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["user"]
        for i in range(self.counter, users):
            content.append({fieldnames[0]: self.created_iam_users[i]})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)
