#!/usr/bin/python3.6
"""
   Encryption utility for information for SSPL.
   Author: Malhar Vora
   Created on: 16-03-2020

   This script uses a Seagate proprietary package called cortx-py-utils. This
   package internally uses a symmetric key encryption algorithm called fernet.
   Read more about fernet at
       1. https://cryptography.io/en/latest/fernet/
       2. https://github.com/fernet/spec/blob/master/Spec.md

   Install package using following command:

   yum install -y cortx-py-utils

   TODO: Understand fernet terminologies and provide hint for errors based on
         those terminologies.
"""
import sys

try:
    from cortx.utils.security.cipher import Cipher
except ImportError as import_error:
    print('Error: cortx-py-utils is not installed.',
          'Please install using yum install -y cortx-py-utils')


def gen_key(cluster_id, service_name):
    """ Generate key for decryption """
    key = Cipher.generate_key(cluster_id, service_name)
    return key


def encrypt(key, text):
    """ Encrypt sensitive data. Ex: RabbitMQ credentials """
    # Before encrypting text we need to convert string to bytes using encode()
    # method
    return Cipher.encrypt(key, text.encode())


def decrypt(key, text):
    """ Decrypt the <text> """
    return Cipher.decrypt(key, text).decode()


def usage():
    """ Print usage """
    print("encryptor.py <encrypt|decrypt> <text> <cluster-id> <service-name>")


def main(args):
    """ Main function """
    ret_code = 0
    if len(args) != 4:
        print('Invalid arguments')
        usage()
        ret_code = 1
    else:
        try:
            operation = args[0].lower()
            text = args[1]
            cluster_id = args[2]
            service_name = args[3]
            print(f'operation: {text}')
            key = gen_key(str(cluster_id), service_name)
            print(f'Key => {key.decode()}\n')
            if operation == 'encrypt':
                encrypted_text = encrypt(key, text)
                print(f'Encryptext Text:')
                print(encrypted_text)
            elif operation == 'decrypt':
                decrypted_text = decrypt(key, text.encode('ascii'))
                print(f'Decryptext Text:')
                print(decrypted_text)
        except Exception as exc:
            ret_code = 1
            print(f'Error: {exc}')
    return ret_code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
