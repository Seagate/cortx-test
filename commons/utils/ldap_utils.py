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

"""LDAP related operations."""
import os
import subprocess
import logging
from base64 import urlsafe_b64encode
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidSignature, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

CORTXSEC_CMD= '/opt/seagate/cortx/extension/cortxsec'

LOGGER = logging.getLogger(__name__)


def decrypt(key: bytes, data: bytes) -> bytes:
    """
    Performs a symmetric decryption of the provided data with the provided key
    """

    try:
        decrypted = Fernet(key).decrypt(data)
    except (InvalidSignature, InvalidToken) as invalid_exception:
        raise CipherInvalidToken("Decryption failed") from invalid_exception
    return decrypted

def gen_key(str1: str, str2: str, *strs):
    """
    Function will be called from generate_key function
    """
    enc_str = str1.encode('utf-8')
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(),
                         length=32,
                         salt=enc_str,
                         iterations=100000,
                         backend=default_backend())
    passwd = str2 + ''.join(strs)
    key = urlsafe_b64encode(kdf.derive(passwd.encode('utf-8')))
    return key

def generate_key(str1: str, str2: str, *strs) -> bytes:
    """
    Function will be invoked by decrypt key function.
    """
    if os.path.exists(CORTXSEC_CMD):
        args = ' '.join(['getkey', str1, str2] + list(strs))
        getkey_cmd = f'{CORTXSEC_CMD} {args}'
        try:
            resp = subprocess.check_output(getkey_cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as process_error:
            raise Exception('Command "{getkey_cmd}" failed') from process_error
        return resp
    generate = gen_key(str1, str2, *strs)
    return generate

def decrypt_secret(secret, cluster_id, decryption_key):
    """
    Function for decrypting the password received from cluster.conf file
    """
    LOGGER.info("Fetching LDAP root user password from Conf Store.")
    try:
        cipher_key = generate_key(cluster_id, decryption_key)
    except KeyError as key_except:
        LOGGER.error("Failed to Fetch keys from Conf store with %s", key_except)
        return None
    try:
        enc_secret = secret.encode("utf-8")
        ldap_root_decrypted_value = decrypt(cipher_key,
                                                    enc_secret)
        return ldap_root_decrypted_value.decode('utf-8')
    except CipherInvalidToken as invalid_exception:
        raise CipherInvalidToken("Decryption failed for password") from invalid_exception

class CipherInvalidToken(Exception):
    """
    Wrapper around actual implementation's decryption exceptions
    """
