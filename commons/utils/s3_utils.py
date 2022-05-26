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
import base64
import datetime
import hashlib
import hmac
import json
import logging
import os
import time
import urllib
from hashlib import md5
from hashlib import sha256
from random import shuffle
from typing import Any

import xmltodict

from commons import constants as const
from commons.utils import assert_utils
from config import S3_CFG

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
    """
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
    """Get sign key."""
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
    region = kwargs.get("region", S3_CFG["region"])
    host = kwargs.get("host")
    algorithm = kwargs.get("algorithm", 'AWS4-HMAC-SHA256')
    canonical_request = create_canonical_request(method, canonical_uri, body, epoch_t, host)
    credential_scope = get_date(epoch_t) + '/' + region + '/' + service + '/' + 'aws4_request'
    string_to_sign = algorithm + '\n' + get_timestamp(epoch_t) + '\n' + credential_scope \
        + '\n' + hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

    return string_to_sign


def sign_request_v4(method=None, canonical_uri='/', body='', epoch_t=None, host='',
                    **kwargs) -> str:
    """
    Calculate aws authentication headers.

    signed_headers = 'host;x-amz-date'
    algorithm = 'AWS4-HMAC-SHA256'
    """
    service = kwargs.get("service", "s3")
    region = kwargs.get("region", S3_CFG["region"])
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
    region = kwargs.get("region", S3_CFG["region"])
    access_key = kwargs.get("access_key")
    secret_key = kwargs.get("secret_key")
    if request is None:
        LOGGER.info("method can not be null")
        raise Exception("Method is None.")
    headers = {}
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
    except ValueError as error:
        LOGGER.error(error)
        return xml_response


# pylint: disable=eval-used, broad-except
def poll(target, *args, condition=None, **kwargs) -> Any:
    """Wait for a function/target to return a certain expected condition."""
    timeout = kwargs.pop("timeout", S3_CFG["sync_delay"])
    step = kwargs.pop("step", S3_CFG["sync_step"])
    expected = kwargs.pop("expected", dict)
    end_time = time.time() + timeout
    while time.time() <= end_time:
        try:
            response = target(*args, **kwargs)
            if condition:
                # Evaluating response with string which is not supported by ast.literal_eval.
                if eval(condition.format(response)):  # nosec
                    return response
            elif isinstance(response, expected) or response:
                return response
        except Exception as response:
            LOGGER.error(response)
        LOGGER.info("SYNC: retrying for %s", str(target.__name__))
        time.sleep(step)

    return target(*args, **kwargs)


def calc_checksum(file_path, part_size=0):
    """Calculate a checksum using encryption algorithm."""
    try:
        hash_digests = []
        with open(file_path, 'rb') as f_obj:
            if part_size and os.stat(file_path).st_size > part_size:
                for chunk in iter(lambda: f_obj.read(part_size), b''):
                    hash_digests.append(sha256(chunk).digest())
            else:
                hash_digests.append(sha256(f_obj.read()).digest())

        return sha256(b''.join(hash_digests)).hexdigest() + '-' + str(len(hash_digests))
    except OSError as error:
        LOGGER.error(str(error))
        raise error from OSError


def calc_contentmd5(data) -> str:
    """
    Calculate Content-MD5 S3 request header value.

    :param data: bytes literal containing the data being sent in an S3 request
    :return: String literal representing the base64 encoded MD5 checksum of the data
    """
    return base64.b64encode(md5(data).digest()).decode('utf-8')  # nosec - s3 ETag based on md5.


def get_multipart_etag(parts):
    """
    Calculate expected ETag for a multipart upload.

    :param parts: List of dict with the format {part_number: (data_bytes, content_md5), ...}
    """
    md5_digests = []
    for part_number in sorted(parts.keys()):
        # comparing ETag with s3 response so calculating it based on md5.
        md5_digests.append(md5(parts[part_number][0]).digest())  # nosec
    multipart_etag = md5(b''.join(md5_digests)).hexdigest() + '-' + str(len(md5_digests))  # nosec
    return f'"{multipart_etag}"'


def get_aligned_parts(file_path, total_parts=1, chunk_size=5242880, random=False) -> dict:
    r"""
    Get aligned parts.

    Create the upload parts dict with aligned part size(limitation: not supported more than 10G).
    https://www.gbmb.org/mb-to-bytes
    Megabytes (MB)	Bytes (B) decimal	Bytes (B) binary
    1 MB	        1,000,000 Bytes	    1,048,576 Bytes
    5 MB	        5,000,000 Bytes	    5,242,880 Bytes
    :param total_parts: No. of parts to be uploaded.
    :param file_path: Path of object file.
    :param chunk_size: chunk size used to read each check default is 5MB.
    :param random: Generate random else sequential part order.
    :return: Parts details with data, checksum.
    """
    try:
        obj_size = os.stat(file_path).st_size
        parts = {}
        part_size = int(int(obj_size) / int(chunk_size)) // int(total_parts)
        with open(file_path, "rb") as fptr:
            i = 1
            while True:
                data = fptr.read(chunk_size * part_size)
                if not data:
                    break
                LOGGER.info("data length %s", str(len(data)))
                parts[i] = [data, calc_contentmd5(data)]
                i += 1
        if random:
            keys = list(parts.keys())
            shuffle(keys)
            parts = {k: parts[k] for k in keys}
        return parts
    except OSError as error:
        LOGGER.error(str(error))
        raise error from OSError


def get_unaligned_parts(file_path, total_parts=1, chunk_size=5242880, random=False) -> dict:
    """
    Create the upload parts dict with unaligned part size(limitation: not supported more than 10G).

    https://www.gbmb.org/mb-to-bytes
    Megabytes (MB)	Bytes (B) decimal	Bytes (B) binary
    1.2 MB          1,200,000 bytes     1,258,291 bytes
    1.5 MB          1,500,000 bytes     1,572,864 bytes
    1.8 MB          1,800,000 bytes     1,887,437 bytes
    1 MB	        1,000,000 Bytes	    1,048,576 Bytes
    5 MB	        5,000,000 Bytes	    5,242,880 Bytes
    :param total_parts: No. of parts to be uploaded.
    :param file_path: Path of object file.
    :param chunk_size: chunk size used to read each check default is 5MB.
    :param random: Generate random else sequential part order.
    :return: Parts details with data, checksum.
    """
    try:
        obj_size = os.stat(file_path).st_size
        parts = {}
        part_size = int(int(obj_size) / int(chunk_size)) // int(total_parts)
        unaligned = [104857, 209715, 314572, 419430, 524288,
                     629145, 734003, 838860, 943718, 1048576]
        with open(file_path, "rb") as file_pointer:
            j = 1
            while True:
                shuffle(unaligned)
                data = file_pointer.read((chunk_size + unaligned[0]) * part_size)
                if not data:
                    break
                LOGGER.info("data_len %s", str(len(data)))
                parts[j] = [data, calc_contentmd5(data)]
                j += 1
        if random:
            keys = list(parts.keys())
            shuffle(keys)
            parts = {e: parts[e] for e in keys}
        return parts
    except OSError as error:
        LOGGER.error(str(error))
        raise error from OSError


def get_precalculated_parts(file_path, part_list, chunk_size=1048576) -> dict:
    """
    Split the source file into the specified part sizes.

    :param file_path: Path of object file.
    :param part_list: List of dict with keys 'part_size' (in bytes) and 'count'
    :param chunk_size: chunk size used to read each check default is 1MB.
    :return: Parts details with data, checksum.
    """
    total_part_list = []
    for part in part_list:
        total_part_list.extend([part['part_size']] * part['count'])
    shuffle(total_part_list)
    parts = {}
    try:
        with open(file_path, "rb") as file_pointer:
            for i, part_size in enumerate(total_part_list, 1):
                data = file_pointer.read(int(part_size * chunk_size))
                parts[i] = [data, calc_contentmd5(data)]
        return parts
    except OSError as error:
        LOGGER.error(str(error))
        raise error from OSError


def create_multipart_json(json_path, parts_list) -> tuple:
    """
    Create json file with all multipart upload details in sorted order.

    parts should be list of {"PartNumber": i, "ETag": part["ETag"]}.
    """
    parts_list = sorted(parts_list, key=lambda d: d['PartNumber'])
    parts = {"Parts": parts_list}
    LOGGER.info("Parts: %s", parts)
    with open(json_path, 'w', encoding="utf-8") as file_obj:
        json.dump(parts, file_obj)

    return os.path.exists(json_path), json_path


def assert_s3_err_msg(rgw_error, cortx_error, cmn_cfg, error):
    """Check the s3 engine type and asserts accordingly."""
    if const.S3_ENGINE_RGW == cmn_cfg:
        assert_utils.assert_in(rgw_error, error.message, error.message)
    else:
        assert_utils.assert_in(cortx_error, error.message, error.message)
