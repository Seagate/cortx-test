# -*- coding: utf-8 -*-
# !/usr/bin/python
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
"""Generate test data for S3 I/O with desired compression, duplication and formats.
Size could be as small as 1 byte to 1 GB.
"""
import os
import logging
import array
import random
import zlib
import hashlib
import string
from typing import Union
from typing import Tuple
from typing import Any
from Crypto.Cipher import AES
from pathlib import Path
from commons import params
from libs.di.file_formats import *

KB = 1024
MB = KB * KB
CMN_BUF = 'i' * MB
DEF_COMPRESS_LEVEL = 4
DEFAULT_DATA_TYPE = 1
ZEROED_DATA_TYPE = 2
U_LIMIT = 10 ** 6
CMPR_RATIOS = (1, 2, 3, 4, 5, 6, 7, 8)
SMALL_BLOCK_SIZES = [4 * KB, 8 * KB, 16 * KB, 32 * KB, 64 * KB, 128 * KB]
MEDIUM_BLOCK_SIZES = [4 * MB, 8 * MB, 16 * MB, 21 * MB, 32 * MB, 64 * MB, 128 * MB]

LOGGER = logging.getLogger(__name__)


def compress(buf, level=DEF_COMPRESS_LEVEL):
    """Compress a buffer with level of specified compression."""
    return zlib.compress(buf, level)


def decompress(buf):
    """Decompress a buffer stream."""
    return zlib.decompress(buf)


class DataGenerator:
    """Data generator for I/O testing.
    Usage:
    d = DataGenerator(c_ratio=2, d_ratio=2)
    seed = d.get_random_seed()
    buf, csum = d.generate(1024 * 1024, seed=seed)
    print(csum)
    d.save_buf_to_file(buf, 1024 * 1024, "test-1")
    """

    def __init__(self,
                 c_ratio: int = 1,
                 embed_csum_in_name: bool = True) -> None:
        self.compression_ratio = c_ratio
        self.append_csum_file_name = embed_csum_in_name
        self.compressibility = int(100 - (1.0 / self.compression_ratio * 100))
        self.secret = '0123456789abcdef' * 2
        self.iv = '0123456789abcdef'

    def generate(self,
                 size: int,
                 datatype: int = DEFAULT_DATA_TYPE,
                 seed: int = None) -> Union[Tuple[str, Any], Tuple[Union[int, bytes], Any]]:

        """Assume size is less than 5GB.
        Keeping de-dupe and compression ratio separate for avoiding complexity in buffer
        stream.

            compressibility (in %) = 100 - (1.0/compression_ratio * 100)

        """
        csum = hashlib.sha1()
        if size == 0:
            buf = ''
            csum.update(buf)
            chksum = csum.hexdigest()
            return buf, chksum

        if datatype == DEFAULT_DATA_TYPE:
            # Ignoring de-dupe ratio for blobs.
            if self.compression_ratio >= 1:
                compressibility = int(100 - (1 / self.compression_ratio * 100))
                buf = self.__get_data(size, compressibility, seed)
        buf = buf.encode('utf-8')[:size]  # hack until better solution is found.
        csum.update(buf)
        chksum = csum.hexdigest()
        return buf, chksum

    @staticmethod
    def get_random_seed(lower: int = 0,
                        upper: int = U_LIMIT) -> int:
        return random.randint(lower, upper)

    def __get_data(self, size, compressibility, seed=None):
        buf = self.__get_uncompressible_buffer(compressibility, size, seed)
        return str(buf) + self.__get_buf(size - len(buf))  # todo can be improved

    def __get_buf(self, size):
        if size <= 0:
            return ''

        if size > len(CMN_BUF):
            return CMN_BUF + self.__get_buf(size - MB)
        else:
            return CMN_BUF[:size]

    def __get_uncompressible_buffer(self, compressibility, size, seed=None):
        if not seed:
            unc_buf = os.urandom(size)
            return unc_buf[0: int((size * (1.0 - compressibility / 100.0)))]
        else:
            buf = array.array('l', [seed] * size).tobytes()
            buf = self.encrypt_buf(buf)
            buf = buf[0: int((size * (1.0 - compressibility / 100.0)))]
            return buf

    def encrypt_buf(self, buf):
        blksz = 16
        sz = len(buf)
        pad = 'z'
        if sz % blksz:
            pad = ' ' * (blksz - sz % blksz)
            buf = ''.join([buf, pad])

        aes = AES.new(self.secret.encode('utf-8'), AES.MODE_OFB, self.iv.encode('utf-8'))
        buf = aes.encrypt(buf)
        if pad:
            buf = buf[:sz]
        return buf

    def save_buf_to_file(self,
                         fbuf: Any,
                         csum: str,
                         size: int,
                         data_folder_prefix: str,
                         min_sz: int = 5,
                         max_sz: int = 10) -> str:
        name = ''
        ext = random.sample(all_extensions, 1)[0]
        for i in range(random.randrange(min_sz, max_sz)):
            name += random.choice(string.ascii_letters + string.digits + '_-')
        if self.append_csum_file_name:
            name += '_' + csum
        name += '_' + 'cx' + ext
        if size < 1024:
            iosize = 1024
        elif (size >= 1024) & (size < 1024 * 1024):
            iosize = 4096
        elif size >= 1024 * 1024:
            iosize = 1024 * 64
        off = 0
        try:
            Path(os.path.join(params.DATAGEN_HOME,
                              data_folder_prefix)).mkdir(parents=True, exist_ok=True)
        except OSError as oe:
            LOGGER.error(f"An error {oe} occurred while creating path.")

        name = os.path.join(params.DATAGEN_HOME, data_folder_prefix, name)
        return self.__save_data_to_file(fbuf, iosize, name, off, size)

    # pylint: disable=max-args, R0201
    def __save_data_to_file(self, fbuf, iosize, name, off, size):
        with open(name, 'wb', 512 * 1024) as fd:  # buffer size
            while off <= size:
                if size < 1024:
                    fd.write(fbuf)
                    off += size
                    break
                if 1024 <= size < iosize:
                    fd.write(fbuf)
                    off += size
                    break
                if off + iosize > size:
                    fd.write(fbuf[off:])
                    off += (size - off)
                    break
                else:
                    fd.write(fbuf[off:off + iosize])
                off += iosize
        return name

    def create_file_from_buf(self,
                             fbuf: Any,
                             name: str,
                             size: int) -> str:
        """ Create file from a buffer with given name/path."""
        if size < 1024:
            iosize = 1024
        elif (size >= 1024) & (size < 1024 * 1024):
            iosize = 4096
        elif size >= 1024 * 1024:
            iosize = 1024 * 64
        off = 0
        return self.__save_data_to_file(fbuf, iosize, name, off, size)

    @staticmethod
    def add_first_byte_to_buffer(buffer, first_byte):
        """
        'non z and f' as first byte of file: then the file is not corrupted during put-object
        'z' as first byte of file: then entire file zeroed during put-object after calculating
         checksum, but before sending data to Motr.
        'f' as first byte of file: then the first byte of the object is
        set to 0 during put-object after calculating checksum,
        but before sending data to Motr.

        :param buffer:
        :param first_byte: is a literal  z,f,Z, F which indicates different types of corruption.
        :return: bytes
        """
        tbuf = bytearray(buffer)
        tbuf[0] = ord(first_byte)
        buffer = bytes(tbuf)
        return buffer


if __name__ == '__main__':
    # Test Data Generator here.
    d = DataGenerator(c_ratio=1)
    buf, csum = d.generate(1024 * 1024 * 5, seed=10)
    print(csum)
    buf = d.add_first_byte_to_buffer(buf, 'z')
    d.save_buf_to_file(buf, csum, 1024 * 1024, "test-1")
