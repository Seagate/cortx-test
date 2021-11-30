#!/usr/bin/env python

from OpenSSL import crypto, SSL
import os

def cert_gen(days=1, file_save_path="."):
    """
    This function is used to generate SSL certificate PEM file
    :param days : number of days the certificate will expire
    :param file_save_path:  The file path to be saved
    :return:  final file path
    """
    emailAddress="administrator_test@seagate.com"
    commonName="Seagate"
    countryName="IN"
    localityName="Pune"
    stateOrProvinceName="MH"
    organizationName="Seagate"
    organizationUnitName="CFT"
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
