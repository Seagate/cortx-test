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
from Crypto import Random
from Crypto.Cipher import AES
from pathlib import Path
from commons import params
from libs.di.file_formats import *

MB = 1024 * 1024
CMN_BUF = 'i' * MB
DEF_COMPRESS_LEVEL = 4
DEFAULT_DATA_TYPE = 1
ZEROED_DATA_TYPE = 2
U_LIMIT = 10 ** 6

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
                 d_ratio: int = 1) -> None:
        self.compression_ratio = c_ratio
        self.dedupe_ratio = d_ratio
        self.compressibility = int(100 - (1.0 / self.compression_ratio * 100))

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
            sum = csum.hexdigest()
            return buf, sum

        if datatype == DEFAULT_DATA_TYPE:
            # Ignoring de-dupe ratio for blobs.
            if self.compression_ratio > 1:
                compressibility = int(100 - (1 / self.compression_ratio * 100))
                buf = self.__get_data(size, compressibility, seed)
        buf = buf.encode('utf-8')[:size]  # hack until better solution is found.
        csum.update(buf)
        sum = csum.hexdigest()
        return buf, sum

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

        secret = '0123456789abcdef' * 2
        iv = '0123456789abcdef'
        aes = AES.new(secret.encode('utf-8'), AES.MODE_OFB, iv.encode('utf-8'))
        buf = aes.encrypt(buf)
        if pad:
            buf = buf[:sz]
        return buf

    def save_buf_to_file(self,
                         fbuf: Any,
                         size: Any,
                         data_folder_prefix: str,
                         min_sz: int = 5,
                         max_sz: int = 10) -> None:
        name = ''
        ext = random.sample(all_extensions, 1)[0]
        for i in range(random.randrange(min_sz, max_sz)):
            name += random.choice(string.ascii_letters + string.digits + '_-')
        name += ext
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


if __name__ == '__main__':
    # Test Data Generator here.
    d = DataGenerator(c_ratio=2, d_ratio=2)
    buf, csum = d.generate(1024 * 1024, seed=10)
    print(csum)
    d.save_buf_to_file(buf, 1024 * 1024, "test-1")
