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

import time
import urllib
import hmac
import datetime
import hashlib
import logging
import json
import boto3
from typing import Any
from botocore.serialize import BaseRestSerializer
from config.s3 import S3_CFG
import xmltodict

LOGGER = logging.getLogger(__name__)


def utf8_encode(msg):
    """Encode the msg into utf-8."""
    return msg.encode('UTF-8')


def utf8_decode(msg):
    """Decode the message into utf-8."""
    return str(msg, 'UTF-8')


def get_date(epoch_t):
    """Get data in YYYYMMDD format."""
    return epoch_t.strftime('%Y%m%d')


def get_timestamp(epoch_t):
    """Get the date timestamp format."""
    return epoch_t.strftime('%Y%m%dT%H%M%SZ')


def get_canonicalized_xamz_headers(headers):
    r"""
    Get the canonicalized xmaz headers.

    if x-amz-* has multiple values then value for that header should be passed as
    list of values eg. headers['x-amz-authors'] = ['Jack', 'Jelly']
    example return value: x-amz-authors:Jack,Jelly\nx-amz-org:Seagate\n
    """
    xamz_headers = ''
    for header in sorted(headers.keys()):
        if header.startswith("x-amz-"):
            if isinstance(headers[header], str):
                xamz_headers += header + ":" + headers[header] + "\n"
            elif isinstance(headers[header], list):
                xamz_headers += header + ":" + ','.join(headers[header]) + "\n"

    return xamz_headers


def create_str_to_sign(http_method, canonical_uri, headers):
    """Create the aws signature from string."""
    str_to_sign = http_method + '\n'
    str_to_sign += headers.get("content-md5", "") + "\n"
    str_to_sign += headers.get("content-type", "") + "\n"
    str_to_sign += headers.get("date", "") + "\n"
    str_to_sign += get_canonicalized_xamz_headers(headers)
    str_to_sign += canonical_uri
    str_to_sign = utf8_encode(str_to_sign)

    return str_to_sign


def create_canonical_request(method, canonical_uri, body, epoch_t, host):
    """Create canonical request."""
    canonical_query_string = ""
    signed_headers = 'host;x-amz-date'
    payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    canonical_headers = 'host:' + host + '\n' + 'x-amz-date:' + get_timestamp(epoch_t) + '\n'
    canonical_request = method + '\n' + canonical_uri + '\n' + canonical_query_string + '\n' + \
        canonical_headers + '\n' + signed_headers + '\n' + payload_hash

    return canonical_request


def sign(key, msg):
    """get sign key."""
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def get_v4_signature_key(key, date_stamp, region_name, service_name):
    """Get the V4 signature key."""
    kdate = sign(('AWS4' + key).encode('utf-8'), date_stamp)
    kregion = sign(kdate, region_name)
    kservice = sign(kregion, service_name)
    ksigning = sign(kservice, 'aws4_request')

    return ksigning


def create_string_to_sign_v4(method='', canonical_uri='', body='', epoch_t=None, **kwargs):
    """Create aws signature from data string."""
    service = kwargs.get("service", "s3")
    region = kwargs.get("region", "US")
    host = kwargs.get("host")
    algorithm = kwargs.get("algorithm", 'AWS4-HMAC-SHA256')
    canonical_request = create_canonical_request(method, canonical_uri, body, epoch_t, host)
    credential_scope = get_date(epoch_t) + '/' + region + '/' + service + '/' + 'aws4_request'
    string_to_sign = algorithm + '\n' + get_timestamp(epoch_t) + '\n' + credential_scope \
        + '\n' + hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

    return string_to_sign


def sign_request_v4(method=None, canonical_uri='/', body='',
                    epoch_t=None, host='', **kwargs) -> str:
    """
    Calculate aws authentication headers.

    signed_headers = 'host;x-amz-date'
    algorithm = 'AWS4-HMAC-SHA256'
    """
    service = kwargs.get("service", "s3")
    region = kwargs.get("region", "US")
    access_key = kwargs.get("access_key")
    secret_key = kwargs.get("secret_key")
    credential_scope = get_date(epoch_t) + '/' + region + '/' + service + '/' + 'aws4_request'
    string_to_sign = create_string_to_sign_v4(
        method, canonical_uri, body, epoch_t, algorithm='AWS4-HMAC-SHA256', host=host,
        service=service, region=region)
    signing_key = get_v4_signature_key(secret_key, get_date(epoch_t), region, service)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    authorization_header = 'AWS4-HMAC-SHA256' + ' ' + 'Credential=' + access_key + '/' + \
                           credential_scope + ', ' + 'SignedHeaders=' + 'host;x-amz-date' + \
                           ', ' + 'Signature=' + signature

    return authorization_header


def get_headers(request=None, endpoint=None, payload=None, **kwargs) -> dict:
    """Get the aws s3 rest headers."""
    # Get host value from url https://iam.seagate.com:9443
    service = kwargs.get("service", "s3")
    region = kwargs.get("region", "US")
    access_key = kwargs.get("access_key")
    secret_key = kwargs.get("secret_key")
    if request is None:
        LOGGER.info("method can not be null")
        raise Exception("Method is None.")
    headers = dict()
    url_parse_result = urllib.parse.urlparse(endpoint)
    epoch_t = datetime.datetime.utcnow()
    body = urllib.parse.urlencode(payload)
    headers['content-type'] = 'application/x-www-form-urlencoded'
    headers['Accept'] = 'text/plain'
    headers['Authorization'] = sign_request_v4(request.upper(),
                                               '/', body, epoch_t,
                                               url_parse_result.netloc,
                                               service=service, region=region,
                                               access_key=access_key, secret_key=secret_key)
    headers['X-Amz-Date'] = get_timestamp(epoch_t)

    return headers


def convert_xml_to_dict(xml_response) -> dict:
    """Convert xml string to json data."""
    try:
        xml_response = xml_response if isinstance(xml_response, str) else xml_response.text
        temp_dict = json.dumps(xmltodict.parse(xml_response))
        json_format = json.loads(temp_dict)

        return json_format
    except Exception as error:
        LOGGER.error(error)
        return xml_response


def poll(target, *args, **kwargs) -> Any:
    """Method to wait for a function/target to return a certain expected condition."""
    timeout = kwargs.pop("timeout", 60)
    step = kwargs.pop("step", 10)
    expected = kwargs.pop("expected", dict)
    end_time = time.time() + timeout
    while time.time() <= end_time:
        try:
            response = target(*args, **kwargs)
            if isinstance(response, expected) or response:
                return response
        except Exception as response:
            LOGGER.error(response)
        time.sleep(step)

    return target(*args, **kwargs)

def create_iam_user(user_name, access_key:str, secret_key:str, **kwargs):
    """
    Create IAM user using given secret and access key.
    """
    use_ssl = kwargs.get("use_ssl", S3_CFG["use_ssl"])
    val_cert = kwargs.get("verify", S3_CFG["validate_certs"])
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    region=S3_CFG["region"]
    iam = boto3.client("iam", use_ssl=use_ssl,
                              verify=val_cert,
                              endpoint_url=endpoint,
                              aws_access_key_id=access_key,
                              aws_secret_access_key=secret_key,
                              region_name=region,
                              **kwargs)
    iam.create_user(UserName=user_name)

def delete_iam_user(user_name, access_key:str, secret_key:str, **kwargs):
    """
    Create IAM user using given secret and access key.
    """
    use_ssl = kwargs.get("use_ssl", S3_CFG["use_ssl"])
    val_cert = kwargs.get("verify", S3_CFG["validate_certs"])
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    region=S3_CFG["region"]
    iam = boto3.client("iam", verify=False,
                              endpoint_url=endpoint,
                              aws_access_key_id=access_key,
                              aws_secret_access_key=secret_key,
                              region_name=region,
                              **kwargs)
    iam.create_user(UserName=user_name)

def create_bucket(bucket_name, access_key:str, secret_key:str, **kwargs):
    """
    Create bucket from give access key and secret key.
    """
    use_ssl = kwargs.get("use_ssl", S3_CFG["use_ssl"])
    val_cert = kwargs.get("verify", S3_CFG["validate_certs"])
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    region=S3_CFG["region"]
    s3 = boto3.resource('s3', verify=False,
                              endpoint_url=endpoint,
                              aws_access_key_id=access_key,
                              aws_secret_access_key=secret_key,
                              region_name=region,
                              **kwargs)
    s3.create_bucket(Bucket=bucket_name)
    result = False
    for bucket in s3.buckets.all():
        if bucket.name == bucket_name:
            result = True
            break
    return result

def delete_bucket(bucket_name, access_key:str, secret_key:str, **kwargs):
    """
    Create bucket from give access key and secret key.
    """
    use_ssl = kwargs.get("use_ssl", S3_CFG["use_ssl"])
    val_cert = kwargs.get("verify", S3_CFG["validate_certs"])
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    region=S3_CFG["region"]
    s3 = boto3.resource('s3', use_ssl=use_ssl,
                              verify=val_cert,
                              endpoint_url=endpoint,
                              aws_access_key_id=access_key,
                              aws_secret_access_key=secret_key,
                              region_name=region,
                              **kwargs)
    s3.create_bucket(Bucket=bucket_name)
    result = False
    for bucket in s3.buckets.all():
        if bucket.name == bucket_name:
            result = True
            break
    return result

def read_write_bucket(object_name:str, bucket_name:str, access_key:str, secret_key:str, **kwargs):
    """
    PUT object in the given bucket with access key and secret key.
    """
    use_ssl = kwargs.get("use_ssl", S3_CFG["use_ssl"])
    val_cert = kwargs.get("verify", S3_CFG["validate_certs"])
    endpoint = kwargs.get("endpoint_url", S3_CFG["s3_url"])
    region=S3_CFG["region"]
    data = open(object_name, 'rb')
    s3 = boto3.resource('s3', verify=False,
                              endpoint_url=endpoint,
                              aws_access_key_id=access_key,
                              aws_secret_access_key=secret_key,
                              region_name=region,
                              **kwargs)
    s3.Bucket(bucket_name).put_object(Key=object_name, Body=data)
    data.close()
    result = False
    for my_bucket_object in s3.Bucket(bucket_name).objects.all(): 
        if my_bucket_object == object_name:
            result = True
            break
    return result
