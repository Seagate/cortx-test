#!/usr/bin/env python
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
"""Script for generating custom certificate."""

import os
from OpenSSL import crypto

# pylint: disable-msg=too-many-locals
def generate_certificate(days=1, file_save_path=".", **kwargs):
    """
    This function is used to generate SSL certificate PEM file
    :param days : number of days the certificate will expire
    :param file_save_path:  The file path to be saved
    :return:  final file path
    """
    email_address = kwargs.get("emailAddress", "administrator_test@seagate.com")
    common_name = kwargs.get("commonName", "Seagate")
    country_name=kwargs.get("countryName", "IN")
    locality_name=kwargs.get("localityName", "Pune")
    state_province_name=kwargs.get("stateOrProvinceName", "MH")
    organization_name=kwargs.get("organizationName", "Seagate")
    organization_unitname=kwargs.get("organizationUnitName", "CFT")
    serial_number=days
    validity_start_in_seconds=0
    key_file = "private.key"
    cert_file = "selfsigned.crt"
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)
    validity_end_in_seconds = 86400 * days

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = country_name
    cert.get_subject().ST = state_province_name
    cert.get_subject().L = locality_name
    cert.get_subject().O = organization_name
    cert.get_subject().OU = organization_unitname
    cert.get_subject().CN = common_name
    cert.get_subject().emailAddress = email_address
    cert.set_serial_number(serial_number)
    cert.gmtime_adj_notBefore(validity_start_in_seconds)
    cert.gmtime_adj_notAfter(validity_end_in_seconds)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha512')
    with open(cert_file, "wt") as cert_file1:
        cert_file1.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"))
    with open(key_file, "wt") as key_file1:
        key_file1.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8"))

    certificate = temp = ""
    with open(cert_file) as cert_file1:
        certificate = cert_file1.read()
    with open(key_file) as key_file1:
        temp = key_file1.read()
    certificate += temp

    file_name = "stx_"+str(days)+".pem"
    file_save_path = str(file_save_path)+os.sep+str(file_name)

    with open (file_save_path, 'w') as file_path:
        file_path.write(certificate)

    os.remove(cert_file)
    os.remove(key_file)
    return file_save_path
