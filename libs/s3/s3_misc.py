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

"""S3 utility Library."""
import os
import logging
import boto3
from config.s3 import S3_CFG
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from libs.s3 import s3_test_lib
from libs.s3 import iam_test_lib

LOGGER = logging.getLogger(__name__)


def create_iam_user(user_name, access_key: str, secret_key: str, **kwargs):
    """
    Create IAM user using given secret and access key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    # endpoint = kwargs.get("endpoint_url", S3_CFG["iam_url"])
    # LOGGER.debug("IAM endpoint : %s", endpoint)
    # s3_cert_path = S3_CFG['s3_cert_path'] if S3_CFG["validate_certs"] else False
    # LOGGER.debug("s3_cert_path : %s", s3_cert_path)
    # iam_test_obj = iam_test_lib.IamTestLib(access_key, secret_key, endpoint, verify=s3_cert_path)
    iam_test_obj = iam_test_lib.IamTestLib(access_key, secret_key)
    iam_test_obj.create_user(user_name)
    LOGGER.debug("Create IAM user command success")
    result = False
    resp = iam_test_obj.list_users()
    user_list = [user["UserName"] for user in resp[1] if "iam_user" in user["UserName"]]
    LOGGER.info("user list: %s", user_list)
    if user_name in user_list:
        LOGGER.debug("IAM user %s found", user_name)
        result = True
    del iam_test_obj
    LOGGER.debug("Verified created IAM user exits")
    return result


def delete_iam_user(user_name, access_key: str, secret_key: str, **kwargs):
    """
    Delete IAM user using given secret and access key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    # endpoint = kwargs.get("endpoint_url", S3_CFG["iam_url"])
    # LOGGER.debug("IAM endpoint : %s", endpoint)
    # region = kwargs.get("region_name", S3_CFG["region"])
    # LOGGER.debug("Region : %s", region)
    # s3_cert_path = S3_CFG['s3_cert_path'] if S3_CFG["validate_certs"] else False
    # LOGGER.debug("s3_cert_path : %s", s3_cert_path)
    # iam_test_obj = iam_test_lib.IamTestLib(access_key, secret_key, endpoint, verify=s3_cert_path)
    iam_test_obj = iam_test_lib.IamTestLib(access_key, secret_key)
    iam_test_obj.delete_user(user_name)
    LOGGER.debug("Delete IAM user command success")
    result = False
    resp = iam_test_obj.list_users()
    user_list = [user["UserName"] for user in resp[1] if "iam_user" in user["UserName"]]
    LOGGER.info("user list: %s", user_list)
    if user_name in user_list:
        LOGGER.debug("IAM user %s found", user_name)
        result = True
    del iam_test_obj
    LOGGER.debug("Verified deleted IAM user does not exits")
    return not result


def create_bucket(bucket_name, access_key: str, secret_key: str, **kwargs):
    """
    Create bucket from give access key and secret key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    # endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    # LOGGER.debug("S3 Endpoint : %s", endpoint)
    # region = kwargs.get("region_name", S3_CFG["region"])
    # LOGGER.debug("Region : %s", region)
    # s3_cert_path = S3_CFG['s3_cert_path'] if S3_CFG["validate_certs"] else False
    # LOGGER.debug("s3_cert_path : %s", s3_cert_path)
    # s3_obj = s3_test_lib.S3TestLib(
    #     access_key, secret_key, endpoint,region=region, verify=s3_cert_path )
    s3_obj = s3_test_lib.S3TestLib(access_key, secret_key)
    s3_obj.create_bucket(bucket_name)
    LOGGER.debug("S3 bucket created")
    _ , bktlist = s3_obj.bucket_list()
    result = False
    LOGGER.info("Bucket list: %s", bktlist)
    if bucket_name in bktlist:
        LOGGER.debug("S3 bucket %s is listed", bucket_name)
        result = True
    del s3_obj
    LOGGER.debug("Verified created bucket exists")
    return result


def delete_objects_bucket(bucket_name, access_key: str, secret_key: str, **kwargs):
    """
    Delete bucket from give access key and secret key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    # endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    # LOGGER.debug("S3 Endpoint : %s", endpoint)
    # region = kwargs.get("region_name", S3_CFG["region"])
    # LOGGER.debug("Region : %s", region)
    # s3_cert_path = S3_CFG['s3_cert_path'] if S3_CFG["validate_certs"] else False
    # LOGGER.debug("s3_cert_path : %s", s3_cert_path)
    # s3_obj = s3_test_lib.S3TestLib(
    #     access_key, secret_key, endpoint,region=region, verify=s3_cert_path )
    s3_obj = s3_test_lib.S3TestLib(access_key, secret_key)
    LOGGER.debug("Delete all associated objects & bucket.")
    s3_obj.delete_bucket(bucket_name, force=True)
    _ , bktlist = s3_obj.bucket_list()
    result = False
    LOGGER.info("Bucket list: %s", bktlist)
    if bucket_name in bktlist:
        LOGGER.debug("S3 bucket %s is listed", bucket_name)
        result = True
    del s3_obj
    LOGGER.debug("Verified bucket is deleted.")
    return not result

def create_put_objects(object_name: str, bucket_name: str,
                       access_key: str, secret_key: str, object_size:int=10, **kwargs):
    """
    PUT object in the given bucket with access key and secret key.
    :param object_size: size of the file in MB.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    # endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    # LOGGER.debug("S3 Endpoint : %s", endpoint)
    # region = kwargs.get("region_name", S3_CFG["region"])
    # LOGGER.debug("Region : %s", region)
    # s3_cert_path = S3_CFG['s3_cert_path'] if S3_CFG["validate_certs"] else False
    # LOGGER.debug("s3_cert_path : %s", s3_cert_path)
    # s3_obj = s3_test_lib.S3TestLib(
    #     access_key, secret_key, endpoint,region=region, verify=s3_cert_path )
    s3_obj = s3_test_lib.S3TestLib(access_key, secret_key)
    LOGGER.debug("Created an object : %s", object_name)
    file_path = os.path.join(TEST_DATA_FOLDER, object_name)
    resp = system_utils.create_file(file_path, object_size)
    if not resp[0]:
        LOGGER.error("Unable to create object file: %s", file_path)
        return False
    data = open(file_path, 'rb')
    LOGGER.debug("Put object: %s in the bucket: %s", object_name, bucket_name)
    resp = s3_obj.put_object(bucket_name, object_name, file_path)
    data.close()
    _ , objlist = s3_obj.object_list(bucket_name)
    result = False
    LOGGER.info("Object list: %s", objlist)
    if object_name in objlist:
        LOGGER.debug("Object %s is listed", object_name)
        result = True
    del s3_obj
    system_utils.remove_file(file_path)
    LOGGER.debug("Verified that Object: %s is present in bucket: %s", object_name, bucket_name)
    return result
