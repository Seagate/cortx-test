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

from OpenSSL import crypto, SSL
import os

def generate_certificate(days=1, file_save_path=".", **kwargs):
    """
    This function is used to generate SSL certificate PEM file
    :param days : number of days the certificate will expire
    :param file_save_path:  The file path to be saved
    :return:  final file path
    """
    emailAddress = kwargs.get("emailAddress", "administrator_test@seagate.com")
    commonName = kwargs.get("commonName", "Seagate")
    countryName=kwargs.get("countryName", "IN")
    localityName=kwargs.get("localityName", "Pune")
    stateOrProvinceName=kwargs.get("stateOrProvinceName", "MH")
    organizationName=kwargs.get("organizationName", "Seagate")
    organizationUnitName=kwargs.get("organizationUnitName", "CFT")
    serialNumber=days
    validityStartInSeconds=0
    KEY_FILE = "private.key"
    CERT_FILE="selfsigned.crt"
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)
    validityEndInSeconds = 86400 * days

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = countryName
    cert.get_subject().ST = stateOrProvinceName
    cert.get_subject().L = localityName
    cert.get_subject().O = organizationName
    cert.get_subject().OU = organizationUnitName
    cert.get_subject().CN = commonName
    cert.get_subject().emailAddress = emailAddress
    cert.set_serial_number(serialNumber)
    cert.gmtime_adj_notBefore(validityStartInSeconds)
    cert.gmtime_adj_notAfter(validityEndInSeconds)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha512')
    with open(CERT_FILE, "wt") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"))
    with open(KEY_FILE, "wt") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8"))

    certificate = temp = ""
    with open(CERT_FILE) as fp:
        certificate = fp.read()
    with open(KEY_FILE) as fp:
        temp = fp.read()
    certificate += temp

    file_name = "stx_"+str(days)+".pem"
    file_save_path = str(file_save_path)+os.sep+str(file_name)

    with open (file_save_path, 'w') as fp:
        fp.write(certificate)

    os.remove(CERT_FILE)
    os.remove(KEY_FILE)
    return file_save_path
