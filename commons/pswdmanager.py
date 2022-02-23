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
"""
Performing the encryption and decryption
"""
import os
import json
import base64
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random as CryptoRandom


def encrypt(secret: str) -> str:
    """
    Encrypt a secret word using AES-CBC mode encryption
    """
    key = get_secrets(secret_ids=['KEY'])['KEY']
    key = key.encode("utf8")
    digest_key = SHA256.new(key).digest()
    secret = secret.encode("utf8")
    init_vec = CryptoRandom.new().read(AES.block_size)
    aes = AES.new(digest_key, AES.MODE_CBC, init_vec)
    padding = AES.block_size - len(secret) % AES.block_size
    secret += bytes([padding]) * padding
    data = init_vec + aes.encrypt(secret)
    return base64.b64encode(data).decode()


def decrypt(enc_secret: str) -> str:
    """
    Decrypt encrypted word using AES-CBC mode decryption
    """
    key = get_secrets(secret_ids=['KEY'])['KEY']
    key = key.encode("utf8")
    digest_key = SHA256.new(key).digest()
    enc_secret = enc_secret.encode("utf8")
    enc_secret = base64.b64decode(enc_secret)
    init_vec = enc_secret[:AES.block_size]
    aes = AES.new(digest_key, AES.MODE_CBC, init_vec)
    data = aes.decrypt(enc_secret[AES.block_size:])
    padding = data[-1]
    if data[-padding:] != bytes([padding]) * padding:
        raise ValueError("Invalid padding...")
    return data[:-padding].decode()


def decrypt_all_passwd(data: dict) -> dict:
    """Decrypt all the values with the key "password"

    :param data: dictionary of configuration which contains encrypted passwords
    :return [type]: return the decrypted passwords
    """
    decrypt_list = [
        "password",
        'new_password',
        'current_password',
        'list_of_passwords',
        'list_special_invalid_char',
        'special_char_pwd',
        'list_special_char_pwd',
        'invalid_password',
        'user_password', 'account_password',
        'root_pwd', 'new_pwd',
        'test_s3account_password',
        'test_csmuser_password',
        's3_acc_passwd',
        'passwd'
    ]
    for key, value in data.items():
        if isinstance(value, dict):
            decrypt_all_passwd(value)
        else:
            if key.lower() in decrypt_list:
                if isinstance(value, list):
                    new_val = []
                    for element in value:
                        new_val.append(decrypt(element))
                    data[key] = new_val
                else:
                    data[key] = decrypt(value)
            if key == 'end' and value == 'end':
                data.pop('end')
                return data


def get_secrets(fpath="secrets.json", secret_ids=None) -> dict:
    """Fetch the secrets from environment or database

    :param fpath: local json file path for reading secrets
    :param secret_ids: keys to be read from json file / environment
    :return [type]: dict of {secrets_id : secret }
    """
    if secret_ids is None:
        secret_ids = ['KEY', 'DB_USER', 'DB_PASSWORD']
    secrets = {}
    for secret_id in secret_ids:
        secret_id = secret_id.upper()
        try:
            secrets[secret_id] = (os.environ[secret_id])
        except KeyError:
            with open(fpath) as file_obj:
                data = json.load(file_obj)
                secrets[secret_id] = data[secret_id]
                os.environ[secret_id] = data[secret_id]
    return secrets
