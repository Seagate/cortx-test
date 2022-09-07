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

"""S3 utility Library."""
import os
import time
import logging
from hashlib import md5
import boto3
from config.s3 import S3_CFG
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib

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
                       verify=S3_CFG['validate_certs'],
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
                       verify=S3_CFG['validate_certs'],
                       endpoint_url=endpoint,
                       aws_access_key_id=access_key,
                       aws_secret_access_key=secret_key,
                       region_name=region,
                       **kwargs)
    LOGGER.debug("IAM client created")
    iam.delete_user(UserName=user_name)
    LOGGER.debug("Delete IAM user command success")
    time.sleep(S3_CFG["delete_account_delay"])
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
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
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
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
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

def delete_objects(bucket_name, access_key: str, secret_key: str, **kwargs):
    """
    Delete all objects from the bucket.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
                                 endpoint_url=endpoint,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key,
                                 region_name=region,
                                 **kwargs)
    LOGGER.debug("S3 boto resource created")
    bucket = s3_resource.Bucket(bucket_name)
    LOGGER.debug("Delete all associated objects.")
    bucket.objects.all().delete()
    result = True
    obj_count = 0
    for _ in bucket.objects.all():
        obj_count = obj_count + 1
    if obj_count != 0:
        LOGGER.debug("all object not deleted")
        result = False
    del s3_resource
    return result

def create_put_objects(object_name: str, bucket_name: str,
                       access_key: str, secret_key: str, object_size:int=10, **kwargs):
    """
    PUT and GET object in the given bucket with access key and secret key.
    :param object_size: size of the file in MB.
    """
    b_size = kwargs.get("block_size", "1M")
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    if "block_size" in kwargs.keys():
        kwargs.pop("block_size")
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
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
    resp = system_utils.create_file(file_path, object_size, b_size=b_size)
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
    Delete specific object from give bucket, access key and secret key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
                                 endpoint_url=endpoint,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key,
                                 region_name=region,
                                 **kwargs)
    LOGGER.debug("S3 boto resource created")
    LOGGER.debug("Delete object : %s in bucket: %s", obj_name, bucket_name)
    s3_resource.Object(bucket_name, obj_name).delete()
    result = True
    for obj in s3_resource.Bucket(bucket_name).objects.all():
        if obj.key == obj_name:
            result = False
            break
    if result is True:
        LOGGER.debug("Verified that Object: %s is deleted", obj_name)
    else:
        LOGGER.debug("Object %s is not deleted", obj_name)
    del s3_resource
    return result

def get_object_size(bucket_name, access_key: str, secret_key: str, **kwargs):
    """
    Function to get object name and size from aws
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
                                 endpoint_url=endpoint,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key,
                                 region_name=region,
                                 **kwargs)
    LOGGER.debug("S3 boto resource created")
    objs = s3_resource.Bucket(bucket_name).objects.all()
    return_dict = {}
    for obj in objs:
        return_dict.update({obj.key:obj.size})
    return return_dict

def get_objects_size_bucket(bucket_name, access_key: str, secret_key: str, **kwargs):
    """
    Function to get total number of objects and total size from aws
    """
    resp = get_object_size(bucket_name, access_key, secret_key, **kwargs)
    return len(resp), sum(resp.values())

def get_objects_list(bucket_name, access_key: str, secret_key: str, **kwargs):
    """
    Function to get list of objects created
    """
    resp = get_object_size(bucket_name, access_key, secret_key, **kwargs)
    obj_lst = []
    for key, value in resp.items():
        obj_lst.append(key)
        LOGGER.debug("values are: %s", value)
    return obj_lst

def get_object_checksum(obj_name, bucket_name, access_key: str, secret_key: str, **kwargs):
    """Get the checksum of the contents of the obj_name in the bucket_name
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
                                 endpoint_url=endpoint,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key,
                                 region_name=region,
                                 **kwargs)
    LOGGER.debug("S3 boto resource created")
    objs = s3_resource.Bucket(bucket_name).objects.all()
    for obj in objs:
        if obj.key == obj_name:
            body = obj.get()['Body'].read()
            file_hash = md5() # nosec
            file_hash.update(body)
            csum = file_hash.hexdigest()
            break
    return csum

def delete_all_buckets(access_key: str, secret_key: str, **kwargs):
    """
    Delete bucket from give access key and secret key.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
                                 endpoint_url=endpoint,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key,
                                 region_name=region,
                                 **kwargs)
    LOGGER.debug("S3 boto resource created")
    for bucket in s3_resource.buckets.all():
        LOGGER.debug("Bucket: %s", bucket.name)
        bucket = s3_resource.Bucket(bucket.name)
        LOGGER.debug("Delete all associated objects.")
        bucket.objects.all().delete()
        LOGGER.debug("Delete bucket : %s", bucket)
        bucket.delete()
    result = not list(s3_resource.buckets.all())
    del s3_resource
    return result

def get_total_used(access_key: str, secret_key: str, **kwargs):
    """Returns total used capacity for given IAM user
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
                                 endpoint_url=endpoint,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key,
                                 region_name=region,
                                 **kwargs)
    LOGGER.debug("S3 boto resource created")
    size =0
    for bucket in s3_resource.buckets.all():
        size += get_objects_size_bucket(bucket.name, access_key, secret_key, **kwargs)[1]
    return size


# pylint: disable=too-many-arguments
def copy_object(access_key: str, secret_key: str, src_bkt: str = None, src_obj: str = None,
                dest_bkt: str = None, dest_obj: str = None, **kwargs):
    """
    Copy of an object that is already stored in Seagate S3 with different permissions.
    :param access_key: Access Key.
    :param secrete_key: Secrete Key.
    :param src_bkt: Source Bucket.
    :param src_obj: Source Object.
    :param dest_bkt: Destination Bucket.
    :param dest_obj: Destination Object.
    :keyword endpoint_url: Endpoint URL, default value S3_CFG["s3_url"]
    :return: True or False.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
                                 endpoint_url=endpoint,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key,
                                 region_name=region,
                                 **kwargs)
    LOGGER.debug("S3 boto resource created")
    copy_source = {'Bucket': src_bkt, 'Key': src_obj}
    s3_resource.Bucket(dest_bkt).copy(copy_source, dest_obj)
    result = False
    for obj in s3_resource.Bucket(dest_bkt).objects.all():
        if obj.key == dest_obj:
            result = True
            break
    del s3_resource
    LOGGER.debug("Verified copied Object: %s is present in destination bucket: %s",
                 dest_obj, dest_bkt)
    return result

def list_bucket(access_key: str, secret_key: str, **kwargs):
    """
    Delete specific object from give bucket, access key and secret key.
    :param access_key: Access Key.
    :param secrete_key: Secrete Key.
    :return: List of buckets.
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    s3_resource = boto3.resource('s3', verify=S3_CFG['validate_certs'],
                                 endpoint_url=endpoint,
                                 aws_access_key_id=access_key,
                                 aws_secret_access_key=secret_key,
                                 region_name=region,
                                 **kwargs)
    LOGGER.debug("S3 boto resource created")
    LOGGER.debug("List buckets")
    bkt_lst = s3_resource.buckets.all()
    del s3_resource
    return bkt_lst

# pylint: disable=too-many-arguments
def multipart_upload(bucket: str, obj: str, access_key: str, secret_key: str,
                     filesize: str, filepath: str, **kwargs):
    """
    It will create IAM user and return s3test obj and s3multipart obj.
    :param bucket: Bucket name.
    :param obj: Object name.
    :param access_key: Access Key.
    :param secrete_key: Secrete Key.
    :param file_size: Size of file.
    :return : repsonse of mulitpart upload
    """
    LOGGER.debug("Access Key : %s", access_key)
    LOGGER.debug("Secret Key : %s", secret_key)
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    parts = kwargs.get("parts", 4)
    LOGGER.debug("S3 Endpoint : %s", endpoint)
    region = S3_CFG["region"]
    LOGGER.debug("Region : %s", region)
    s3_mp_test_obj = S3MultipartTestLib(access_key=access_key, secret_key=secret_key,
                                        endpoint_url=S3_CFG["s3_url"])
    return s3_mp_test_obj.simple_multipart_upload(bucket, obj, filesize, filepath, parts)
