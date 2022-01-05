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

LOGGER = logging.getLogger(__name__)


def create_iam_user(user_name, access_key: str, secret_key: str, **kwargs):
    """
    Create IAM user using given secret and access key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["iam_url"])
    LOGGER.debug("IAM endpoint : %s", endpoint)

    region = kwargs.get("region_name", S3_CFG["region"])
    LOGGER.debug("Region : %s", region)

    iam = boto3.client("iam",
                       verify=False,
                       endpoint_url=endpoint,
                       aws_access_key_id=access_key,
                       aws_secret_access_key=secret_key,
                       region_name=region,
                       **kwargs)
    LOGGER.debug("IAM client created")
    iam.create_user(UserName=user_name)
    LOGGER.debug("Create IAM user command success")
    result = False
    for iam_user in iam.list_users()["Users"]:
        if user_name == iam_user['UserName']:
            LOGGER.debug("IAM user %s found", iam_user)
            result = True
    del iam
    LOGGER.debug("Verified created IAM user exits")
    return result


def delete_iam_user(user_name, access_key: str, secret_key: str, **kwargs):
    """
    Delete IAM user using given secret and access key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["iam_url"])
    LOGGER.debug("IAM endpoint : %s", endpoint)

    region = kwargs.get("region_name", S3_CFG["region"])
    LOGGER.debug("Region : %s", region)

    iam = boto3.client("iam",
                       verify=False,
                       endpoint_url=endpoint,
                       aws_access_key_id=access_key,
                       aws_secret_access_key=secret_key,
                       region_name=region,
                       **kwargs)
    LOGGER.debug("IAM client created")

    iam.delete_user(UserName=user_name)
    LOGGER.debug("Delete IAM user command success")

    result = False
    for iam_user in iam.list_users()["Users"]:
        if user_name == iam_user['UserName']:
            result = True
    del iam
    LOGGER.debug("Verified deleted IAM user does not exits")
    return not result


def create_bucket(bucket_name, access_key: str, secret_key: str, **kwargs):
    """
    Create bucket from give access key and secret key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)

    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)

    s3_resource = boto3.resource('s3', verify=False,
                        endpoint_url=endpoint,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=region,
                        **kwargs)
    LOGGER.debug("S3 boto resource created")

    s3_resource.create_bucket(Bucket=bucket_name)
    LOGGER.debug("S3 bucket created")

    result = False
    for bucket in s3_resource.buckets.all():
        if bucket.name == bucket_name:
            LOGGER.debug("S3 bucket %s is listed", bucket)
            result = True
            break
    del s3_resource
    LOGGER.debug("Verified created bucket exists")
    return result


def delete_objects_bucket(bucket_name, access_key: str, secret_key: str, **kwargs):
    """
    Delete bucket from give access key and secret key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)

    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)

    s3_resource = boto3.resource('s3', verify=False,
                        endpoint_url=endpoint,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=region,
                        **kwargs)
    LOGGER.debug("S3 boto resource created")

    bucket = s3_resource.Bucket(bucket_name)
    LOGGER.debug("Delete all associated objects.")
    bucket.objects.all().delete()

    LOGGER.debug("Delete bucket : %s", bucket)
    bucket.delete()

    result = False
    for bucket in s3_resource.buckets.all():
        if bucket.name == bucket_name:
            result = True
            break
    del s3_resource
    LOGGER.debug("Verified bucket is deleted.")
    return not result


def create_put_objects(object_name: str, bucket_name: str,
                       access_key: str, secret_key: str, object_size:int=10, **kwargs):
    """
    PUT object in the given bucket with access key and secret key.
    :param object_size: size of the file in MB.
    """

    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)

    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)

    s3_resource = boto3.resource('s3', verify=False,
                        endpoint_url=endpoint,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=region,
                        **kwargs)
    LOGGER.debug("S3 boto resource created")

    LOGGER.debug("Created an object : %s", object_name)
    if not os.path.exists(TEST_DATA_FOLDER):
        os.mkdir(TEST_DATA_FOLDER)
    file_path = os.path.join(TEST_DATA_FOLDER, object_name)
    resp = system_utils.create_file(file_path, object_size)
    if not resp[0]:
        LOGGER.error("Unable to create object file: %s", file_path)
        return False
    data = open(file_path, 'rb')
    LOGGER.debug("Put object: %s in the bucket: %s", object_name, bucket_name)
    s3_resource.Bucket(bucket_name).put_object(Key=object_name, Body=data)
    data.close()

    result = False
    for my_bucket_object in s3_resource.Bucket(bucket_name).objects.all():
        if my_bucket_object.key == object_name:
            result = True
            break
    del s3_resource
    system_utils.remove_file(file_path)

    LOGGER.debug("Verified that Object: %s is present in bucket: %s", object_name, bucket_name)
    return result

def delete_object(obj_name, bucket_name, access_key: str, secret_key: str, **kwargs):
    """
    Delete bucket from give access key and secret key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)

    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)

    s3_resource = boto3.resource('s3', verify=False,
                        endpoint_url=endpoint,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=region,
                        **kwargs)
    LOGGER.debug("S3 boto resource created")

    LOGGER.debug("Delete object : %s in bucket: %s", obj_name, bucket_name)
    s3_resource.Object(bucket_name, obj_name).delete()
    del s3_resource
    return True
