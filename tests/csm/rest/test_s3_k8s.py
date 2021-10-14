#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""Tests operations on S3 Users using REST API"""

import json
import logging
import pytest
import time
import re
import os
import subprocess
import configparser
import yaml
from commons.constants import Rest as const
from commons import cortxlogging
from commons import configmanager
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_s3user import RestS3user
from commons.utils.system_utils import run_remote_cmd
from commons.utils import assert_utils
from commons.helpers.node_helper import Node
from commons import constants as cons
from config import CMN_CFG
from config import S3_CFG
from config import CSM_CFG
from commons.utils.system_utils import run_remote_cmd
from cryptography.fernet import Fernet
from commons.utils.config_utils import get_config
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from cryptography.fernet import InvalidSignature, InvalidToken
from base64 import urlsafe_b64encode
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

cortxsec_cmd = '/opt/seagate/cortx/extension/cortxsec'

class TestS3accountK8s:
    """S3 user test class"""
    @classmethod
    def setup_method(self):
        """
        Function will be invoked test before and after yield part each test case execution.
        """
        self.log = logging.getLogger(__name__)
        self.config = configparser.ConfigParser()
        self.log.info("STARTED: test setup.")
        self.s3_rest_obj = S3AccountOperationsRestAPI()
        self.host = CMN_CFG["nodes"][0]["hostname"]
        self.uname = CMN_CFG["nodes"][0]["username"]
        self.passwd = CMN_CFG["nodes"][0]["password"]
        self.nd_obj = Node(hostname=self.host, username=self.uname, password=self.passwd)
        self.s3acc_name = "{}_{}".format("cli_s3_acc", int(time.perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.remote_path = cons.CLUSTER_CONF_PATH
        self.local_path = cons.LOCAL_CONF_PATH

    def ldap_search(self, ip_addr: str = None, user_name: str = None,
                    password: str = None):
        """Functionality to form and execute ldapsearch command"""
        if ip_addr is not None:
            ldap_search_cmd = cons.LDAP_SEARCH_DATA + " -H ldap://{}".format(ip_addr)
        if user_name is not None:
            ldap_search_cmd = ldap_search_cmd + " -D \"cn={0},dc=seagate,dc=com\"".format(user_name)
        if password is not None:
            ldap_search_cmd = ldap_search_cmd + " -w {}".format(password)
        self.log.info(ldap_search_cmd)
        response = run_remote_cmd(
            cmd=ldap_search_cmd,
            hostname=self.host,
            username=self.uname,
            password=self.passwd,
            read_lines=True)
        self.log.info("printing response from ldap function")
        self.log.info(response)
        return response

    def get_cluster_ip(self, resp1):
        self.log.info("extract cluster ip")
        data = str(resp1, 'UTF-8')
        data = data.split("\n")
        for line in data:
            if "openldap-svc" in line:
                line_found = line
                res = re.sub(' +', ' ', line_found)
                res = res.split()[2]
                self.log.info(res)
                return res

    def decrypt(self, key: bytes, data: bytes) -> bytes:
        """
        Performs a symmetric decryption of the provided data with the provided key
        """

        try:
            decrypted = Fernet(key).decrypt(data)
        except (InvalidSignature, InvalidToken):
            raise CipherInvalidToken(f'Decryption failed')
        return decrypted

    def gen_key(self, str1: str, str2: str, *strs):
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(),
                         length=32,
                         salt=str1.encode('UTF-8'),
                         iterations=100000,
                         backend=default_backend())
        passwd = str2 + ''.join(strs)
        key = urlsafe_b64encode(kdf.derive(passwd.encode('utf-8')))
        return key

    def generate_key(self, str1: str, str2: str, *strs) -> bytes:
        if os.path.exists(cortxsec_cmd):
            args = ' '.join(['getkey', str1, str2] + list(strs))
            getkey_cmd = f'{cortxsec_cmd} {args}'
            try:
                resp = subprocess.check_output(getkey_cmd.split(), stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                raise Exception(f'Command "{getkey_cmd}" failed with the output: {e.output}') from e
            return resp
        else:
            generate = self.gen_key(str1, str2, *strs)
            return generate

    def _decrypt_secret(self, secret, cluster_id, decryption_key):
        self.log.info("Fetching LDAP root user password from Conf Store.")
        try:
            self.log.info("inside try")
            cipher_key = self.generate_key(cluster_id,decryption_key)
        except OSError:
            self.log.info("inside first except")
            self.log.error(f"Failed to Fetch keys from Conf store.")
            return None
        except Exception as e:
            return None
        try:
            ldap_root_decrypted_value = self.decrypt(cipher_key,
                                                secret.encode("utf-8"))
            return ldap_root_decrypted_value.decode('utf-8')
        except CipherInvalidToken as error:
            self.log.error(f"Decryption for LDAP root user password Failed. {error}")
            raise CipherInvalidToken(f"Decryption for LDAP root user password Failed. {error}")


    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_k8s_user
    @pytest.mark.tags("TEST-28934")
    def test_28934(self):
        """This test validates the presence of password in ldapsearch output"""
        #S3 account creation could not be executed due to setup issue
        self.log.info("Step 1: Create s3account s3acc.")
        resp = self.s3_rest_obj.create_s3_account(
           self.s3acc_name, self.s3acc_email, self.s3acc_passwd)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 2: Get cluster IP of openldap")
        resp_node = self.nd_obj.execute_cmd(cmd="kubectl get svc",
                                        read_lines=False,
                                        exc=False)
        cluster_ip = self.get_cluster_ip(resp_node)
        self.log.info("printing ip in test after calling function")
        self.log.info(cluster_ip)
        resp = self.nd_obj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        stream = open(self.local_path, 'r')
        data = yaml.load(stream, Loader=yaml.FullLoader)
        admin_user = data['cortx']['external']['openldap']['admin']
        secret = data['cortx']['external']['openldap']['secret']
        self.log.info(secret)
        cluster_id = data["cluster"]["id"]
        self.log.info(cluster_id)
        admin_passwd = self._decrypt_secret(secret,cluster_id,"cortx")
        self.log.info(admin_passwd)
        #Follwing command takes too long to execute
        login_ldap_pod = "kubectl exec -it symas-openldap-pod -- /bin/bash"
        resp_node = self.nd_obj.execute_cmd(cmd=login_ldap_pod,
                                        read_lines=False,
                                        exc=False)
        self.log.info(resp_node)
        self.log.info("Step 3: call ldapsearch command form method")
        status, result = self.ldap_search(ip_addr=cluster_ip, user_name=admin_user,
                                password=admin_passwd)
        self.log.info("printing response and type")
        self.log.info("Step 4: Search for s3 account password in output")
        for resp in result:
             if "password" in resp:
                 self.log.info("password is present")
             else:
                 self.log.info("password is not present")
                 self.log.info("Test passed")
        self.log.info("##############Test Passed##############")

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_k8s_user
    @pytest.mark.tags("TEST-28935")
    def test_28935(self):
        """This test validates the presence of secret key in ldapsearch output"""
        #S3 account creation could not be executed due to setup issue
        self.log.info("Step 1: Create s3account s3acc.")
        resp = self.s3_rest_obj.create_s3_account(
           self.s3acc_name, self.s3acc_email, self.s3acc_passwd)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 2: Get cluster IP of openldap")
        resp_node = self.nd_obj.execute_cmd(cmd="kubectl get svc",
                                        read_lines=False,
                                        exc=False)
        cluster_ip = self.get_cluster_ip(resp_node)
        self.log.info("printing ip in test after calling function")
        self.log.info(cluster_ip)
        resp = self.nd_obj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        stream = open(self.local_path, 'r')
        data = yaml.load(stream, Loader=yaml.FullLoader)
        admin_user = data['cortx']['external']['openldap']['admin']
        secret = data['cortx']['external']['openldap']['secret']
        self.log.info(secret)
        cluster_id = data["cluster"]["id"]
        self.log.info(cluster_id)
        admin_passwd = self._decrypt_secret(secret,cluster_id,"cortx")
        self.log.info(admin_passwd)
        #Follwing command takes too long to execute
        login_ldap_pod = "kubectl exec -it symas-openldap-pod -- /bin/bash"
        resp_node = self.nd_obj.execute_cmd(cmd=login_ldap_pod,
                                        read_lines=False,
                                        exc=False)
        self.log.info(resp_node)
        self.log.info("Step 3: call ldapsearch command form method")
        status, result = self.ldap_search(ip_addr=cluster_ip, user_name=admin_user,
                                password=admin_passwd)
        self.log.info("printing response and type")
        self.log.info("Step 4: Search for s3 account password in output")
        for resp in result:
             if "secret_key "in resp:
                 self.log.info("secret key is present")
             else:
                 self.log.info("secret key is not present")
                 self.log.info("Test passed")
        self.log.info("##############Test Passed##############")
