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
import urllib
import hmac
import datetime
import hashlib
import logging
import json
import xmltodict
from hashlib import md5
from random import shuffle


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


def calc_etag(input_file, part_size=0):
    """Calculating an S3 ETag using Python md5 algorithm"""
    try:
        md5_digests = list()
        with open(input_file, 'rb') as f:
            if part_size and os.stat(input_file).st_size < part_size:
                for chunk in iter(lambda: f.read(part_size), b''):
                    md5_digests.append(md5(chunk).digest())
            else:
                md5_digests.append(md5(f.read(part_size)).digest())

        return md5(b''.join(md5_digests)).hexdigest() + '-' + str(len(md5_digests))
    except OSError as error:
        LOGGER.error(str(error))
        raise error from OSError


def get_aligned_parts(file_path, total_parts=1, random=False) -> dict:
    """
    Create the upload parts dict with aligned part size.

    https://www.gbmb.org/mb-to-bytes
    Megabytes (MB)	Bytes (B) decimal	Bytes (B) binary
    1 MB	        1,000,000 Bytes	    1,048,576 Bytes
    5 MB	        5,000,000 Bytes	    5,242,880 Bytes
    :param total_parts: No. of parts to be uploaded.
    :param file_path: Path of object file.
    :param random: Generate random else sequential part order.
    :return: Dict of uploaded parts.
    """
    try:
        obj_size = os.stat(file_path).st_size
        parts = dict()
        part_size = int(obj_size) // int(total_parts)
        with open(file_path, "rb") as file_pointer:
            i = 1
            while True:
                data = file_pointer.read(5242880 * part_size)
                if not data:
                    break
                LOGGER.info("data_len %s", str(len(data)))
                parts[i] = data
                i += 1
        if random:
            keys = list(parts.keys())
            shuffle(keys)
            parts = dict({(k, parts[k]) for k in keys})

        return parts
    except OSError as error:
        LOGGER.error(str(error))
        raise error from OSError


def get_unaligned_parts(file_path, total_parts=1, random=False) -> dict:
    """
    Create the upload parts dict with unaligned part size.

    https://www.gbmb.org/mb-to-bytes
    Megabytes (MB)	Bytes (B) decimal	Bytes (B) binary
    1.2 MB          1,200,000 bytes     1,258,291 bytes
    1.5 MB          1,500,000 bytes     1,572,864 bytes
    1.8 MB          1,800,000 bytes     1,887,437 bytes
    1 MB	        1,000,000 Bytes	    1,048,576 Bytes
    5 MB	        5,000,000 Bytes	    5,242,880 Bytes
    :param total_parts: No. of parts to be uploaded.
    :param file_path: Path of object file.
    :param random: Generate random else sequential part order.
    :return: Dict of uploaded parts.
    """
    try:
        obj_size = os.stat(file_path).st_size
        parts = dict()
        part_size = int(obj_size) // int(total_parts)
        unaligned = [258291, 572864, 887437]
        with open(file_path, "rb") as file_pointer:
            i = 1
            while True:
                shuffle(unaligned)
                data = file_pointer.read(5242880 * part_size * unaligned[0])
                if not data:
                    break
                LOGGER.info("data_len %s", str(len(data)))
                parts[i] = data
                i += 1
        if random:
            keys = list(parts.keys())
            shuffle(keys)
            parts = dict({(k, parts[k]) for k in keys})

        return parts
    except OSError as error:
        LOGGER.error(str(error))
        raise error from OSError
