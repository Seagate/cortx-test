#!/usr/bin/python
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
import random
import os
import sys
import string
from multiprocessing import Process, Value, Lock
from struct import pack
from platform import system
from struct import unpack

randmax = 2147483647 / 256

fileextbin1k = 646 * ['dat'] + 1074 * ['png'] + 105 * ['sol'] + 89 * ['jpg'] + 72 * ['lex'] + 7739 * ['gif'] + 947 * [
    'cookie'] + 642 * ['aae'] + 324 * ['sth'] + 285 * ['tbl'] + 262 * ['old'] + 248 * ['vcrd'] + 150 * [
                   'settingcontent-ms'] + 140 * ['lock'] + 99 * ['rtf'] + 81 * ['fingerprint'] + 40 * ['md'] + 48 * [
                   'pset']

fileexttxt1k = 5717 * ['txt'] + 1584 * ['xml'] + 9339 * [''] + 3723 * ['json'] + 865 * ['url'] + 417 * ['lnk'] + 252 * [
    'htm'] + 424 * ['log'] + 200 * ['ini'] + 138 * ['log2'] + 159 * ['html'] + 260 * ['js'] + 253 * ['usage'] + 152 * [
                   'conf'] + 124 * ['localstorage-journal'] + 103 * ['css'] + 88 * ['svg']

fileextbin10k = 1038 * ['dat'] + 919 * ['png'] + 2565 * ['jpg'] + 560 * ['gif'] + 119 * ['cookie'] + 382 * [
    'settingcontent-ms'] + 111 * ['md'] + 551 * ['xlsx'] + 372 * ['bmp'] + 184 * ['cache'] + 168 * ['glox'] + 157 * [
                    'pdf'] + 137 * ['download'] + 120 * ['wav'] + 86 * ['onetoc2'] + 65 * ['wpl'] + 60 * ['logo',
                                                                                                          'woff2']

fileexttxt10k = 1480 * ['txt'] + 558 * ['xml'] + 4491 * [''] + 738 * ['json'] + 411 * ['lnk'] + 312 * ['htm'] + 7239 * [
    'log'] + 128 * ['ini'] + 102 * ['html'] + 655 * ['js'] + 79 * ['localstorage'] + 466 * ['css'] + 111 * [
                    'svg'] + 161 * ['sqm'] + 104 * ['vcf'] + 100 * ['log1']

fileextbin100k = 320 * ['dat'] + 341 * ['png'] + 835 * ['jpg'] + 420 * ['gif'] + 5890 * ['xlsx'] + 183 * [
    'bmp'] + 414 * ['cache'] + 6296 * ['pdf'] + 147 * ['download'] + 1745 * ['wav'] + 5318 * ['docx'] + 4896 * [
                     'doc'] + 3905 * ['xls'] + 181 * ['one'] + 169 * ['mui'] + 139 * ['ico'] + 126 * ['xlsb'] + 116 * [
                     'etl'] + 102 * ['exe'] + 90 * ['db'] + 75 * ['dotx'] + 74 * ['pptx'] + 71 * ['dll'] + 62 * [
                     'tmp'] + 61 * ['png0'] + 57 * ['zip'] + 55 * ['dotm']

fileexttxt100k = 733 * ['txt'] + 170 * ['xml'] + 3158 * [''] + 886 * ['json'] + 226 * ['htm'] + 58 * ['log'] + 577 * [
    'js'] + 312 * ['css']

fileextbin1m = 260 * ['dat'] + 154 * ['png'] + 1633 * ['jpg'] + 2453 * ['xlsx'] + 55 * ['bmp'] + 93 * [
    'cache'] + 7790 * ['pdf'] + 81 * ['download'] + 485 * ['wav'] + 2376 * ['docx'] + 2520 * ['doc'] + 2237 * [
                   'xls'] + 142 * ['one'] + 76 * ['ico'] + 71 * ['etl'] + 49 * ['exe'] + 908 * ['pptx'] + 189 * [
                   'dll'] + 57 * ['zip'] + 299 * ['ppt'] + 242 * ['xsl'] + 155 * ['thmx'] + 141 * ['xlsm'] + 56 * [
                   'xltx'] + 53 * ['idx'] + 44 * ['itc']

fileexttxt1m = 94 * ['txt'] + 123 * ['xml'] + 1301 * [''] + 88 * ['htm'] + 95 * ['log'] + 260 * ['js'] + 231 * [
    'css'] + 76 * ['html'] + 47 * ['msg']

fileextbin10m = 35 * ['dat'] + 46 * ['png', 'avi'] + 2631 * ['jpg'] + 1051 * ['xlsx'] + 1897 * ['pdf'] + 120 * [
    'download'] + 430 * ['docx'] + 284 * ['doc'] + 863 * ['xls'] + 66 * ['one'] + 49 * ['etl'] + 27 * ['exe'] + 1226 * [
                    'pptx'] + 239 * ['dll'] + 101 * ['zip'] + 232 * ['ppt'] + 147 * ['thmx'] + 47 * ['xlsm'] + 143 * [
                    'pma'] + 59 * ['ldb'] + 45 * ['jpeg', 'dotx'] + 28 * ['mov'] + 24 * ['bz2', 'edb'] + 20 * [
                    'jrs'] + 16 * ['msmessagestore'] + 15 * ['dmp'] + 14 * ['mp4']

fileexttxt10m = 15 * ['xml'] + 435 * [''] + 53 * ['log'] + 19 * ['js'] + 142 * ['msg']

fileextbin100m = 4 * ['dat'] + 2 * ['jpg'] + 78 * ['xlsx'] + 201 * ['pdf'] + 11 * ['docx'] + 20 * ['doc'] + 79 * [
    'xls'] + 18 * ['one'] + 3 * ['etl'] + 12 * ['exe'] + 109 * ['pptx'] + 31 * ['dll'] + 34 * ['zip'] + 13 * [
                     'ppt'] + 18 * ['mov'] + 57 * ['bz2'] + 3 * ['mp4'] + 8 * ['msi'] + 7 * ['mig'] + 4 * ['3gp', 'avi',
                                                                                                           'db'] + 3 * [
                     'bak'] + 3 * ['bmp'] + 3 * ['cab', 'edb'] + 3 * ['partial'] + 3 * ['sqlite'] + 3 * [
                     'themepack'] + 2 * ['arf'] + 2 * ['chm']

fileexttxt100m = 3 * ['xml'] + 16 * [''] + 5 * ['msg'] + 4 * ['txt']

fileextbin1g = ['xlsx'] + 8 * ['pdf'] + 3 * ['exe'] + 2 * ['pptx'] + 3 * ['zip'] + 4 * ['mov'] + 2 * ['bz2'] + 1 * [
    'mp4'] + ['bak'] + 3 * ['pst'] + 4 * ['wrf'] + 8 * ['tar'] + ['mig']

fileexttxt1g = ['']

fileextbin10g = ['7z'] + 7 * ['pst'] + ['ost'] + ['old']

fileexttxt10g = []

binary = fileextbin1g + fileextbin10g + fileextbin100m + fileextbin10m + fileextbin1m + fileextbin100k + fileextbin10k + fileextbin1k
ascii = fileexttxt1g + fileexttxt100m + fileexttxt10m + fileexttxt1m + fileexttxt100k + fileexttxt10k + fileexttxt1k

dir_depth_dist = [0.47, 2.85, 1.61, 4.48, 7.91, 20.19, 15.39, 9.94, 6.81, 6.95, 4.31, 4.12, 14.95]
dir_depth_variation = [1, 4, 3, 3, 4, 5, 4, 5, 3, 4, 2, 2, 3]
files_depth_dist = [0.01, 1.85, 2.39, 4.97, 7.24, 12.56, 19.25, 14.49, 14.77, 12.45, 4.98, 1.44, 3.61]
files_depth_variation = [4, 6, 3, 3, 3, 3, 2, 5, 14, 6, 7, 3, 4]
fileslevel = len(files_depth_dist)


def randname(min=4, max=10):
    a = ''
    for i in range(random.randrange(min, max)):
        a = a + random.choice(string.ascii_letters + string.digits)
    return a


def randfilename(size, min=5, max=40):
    fname = ''
    for i in range(random.randrange(min, max)):
        fname += random.choice(string.ascii_letters + string.digits + '_-')

    if size < 1024:
        ext = random.choice(fileexttxt1k + fileextbin1k)
    elif (size >= 1024) & (size < 10240):
        ext = random.choice(fileexttxt10k + fileextbin10k)
    elif (size >= 10240) & (size < 102400):
        ext = random.choice(fileexttxt100k + fileextbin100k)
    elif (size >= 102400) & (size < 1024 * 1024):
        ext = random.choice(fileexttxt1m + fileextbin1m)
    elif (size >= 1024 * 1024) & (size < 1024 * 10240):
        ext = random.choice(fileexttxt10m + fileextbin10m)
    elif (size >= 1024 * 10240) & (size < 10240 * 10240):
        ext = random.choice(fileexttxt100m + fileextbin100m)
    elif (size >= 10240 * 10240) & (size < 1024 * 1024 * 1024):
        ext = random.choice(fileexttxt1g + fileextbin1g)
    elif size >= 1024 * 1024 * 1024:
        ext = random.choice(fileextbin10g)
    return fname, ext


def randtext(bytes):
    a = ''
    for it in range(bytes / 8):
        a += ''.join(random.choice(string.printable) for _ in range(4)) + 4 * ' '
    if (bytes % 8) == 0:
        pass
    else:
        b = ''.join(random.choice(string.printable) for _ in range(4)) + 4 * ' '
        a += b[0:bytes % 8]
    return a


def randbytes(bytes):
    a = ''.join(pack('q', random.randrange(randmax))
                for _ in range(bytes / 8))
    if (bytes % 8) == 0:
        pass
    else:
        a += (''.join(pack('q', random.randrange(randmax))))[0:bytes % 8]
    return a


def bufferbin(size):
    buf = ''
    for i in range(size / 8):
        buf = buf + pack('q', random.randrange(randmax))
    return buf


def buffertext(bytes):
    a = ''
    for it in range(bytes / 8):
        a += ''.join(random.choice(string.printable) for _ in range(4)) + 4 * ' '
    if (bytes % 8) == 0:
        pass
    else:
        b = ''.join(random.choice(string.printable) for _ in range(4)) + 4 * ' '
        a += b[0:bytes % 8]
    return a


def make_dirs(name, number):
    dirs = []
    for i in range(0, number, 1):
        dirname = randname()
        path = name + '/' + dirname
        dirs.append(path)
    return dirs


def make_dirtree(topdir, depth, number):
    all_dirs = []
    top = [topdir]
    temp = []
    if (depth <= fileslevel):
        filefact = int(round(1000.0 * files_depth_dist[-depth] / len(top)))
        all_dirs.extend(top * filefact)
    depth -= 1
    while (depth):
        variation = dir_depth_variation[-depth]
        nextdirs = int(round((dir_depth_dist[-depth - 1] * number / 100)))
        if (len(top) > nextdirs):
            samplesize = nextdirs
        else:
            samplesize = len(top)

        for x in random.sample(variation * top, samplesize):
            numberdirs = int(nextdirs / samplesize)
            temp.extend(make_dirs(x, numberdirs))
        top = temp
        print(top)

        temp = []
        if depth <= fileslevel:
            filefact = int(round(1000.0 * files_depth_dist[-depth] / len(top)))
            filevariation = files_depth_variation[-depth]
            sampletop = top
            for it in range(7 * filevariation):
                sampletop = random.sample(filevariation * sampletop, len(top))
            all_dirs.extend(filefact * (sampletop + top))

        depth -= 1
    return all_dirs


def create_fileset(fsize_percent, randseed, numfiles, alldirs, lock):
    mycwd = os.getcwd()
    isWindows = False
    if system() == 'Windows':
        isWindows = True
    fs = 0
    random.seed(randseed)
    block = 1024 * 1024 * 40
    buftxt = buffertext(block)
    bufbin = bufferbin(block)
    for fs_pc in fsize_percent:
        isize = fs_pc[0] - fs
        for fno in range(int(round(fs_pc[1] * numfiles / 100))):
            randno = random.randrange(randmax)
            if (isize > 1):
                size = fs + isize * randno / randmax
            else:
                size = fs + isize
            filename, ext = randfilename(size)
            dira = random.choice(alldirs)
            if ext:
                filename = filename + '.' + ext
            lock.acquire()
            printstring = (str(dira + '/' + filename), size)
            print(printstring)
            lock.release()

            if isWindows:
                dira = '\\\\?\\' + mycwd + '\\' + dira.replace('/', '\\')
                filename = dira + '\\' + filename
            else:
                filename = dira + '/' + filename

            try:
                os.makedirs(dira)
            except:
                pass
            f = open(filename, 'wb', 512 * 1024)
            if (size < 1024):
                iosize = 128
            elif (size >= 1024) & (size < 1024 * 1024):
                iosize = 4096
            elif (size >= 1024 * 1024):
                iosize = 1024 * 64

            sizew = size / iosize
            randn = len(bufbin[:-iosize])
            for z in range(0, sizew, 1):
                noff = random.randrange(randn)
                if ext in binary:
                    f.write(bufbin[noff:noff + iosize])
                else:
                    f.write(buftxt[noff:noff + iosize])
            x = size - f.tell()
            if (x > 0):
                if ext in binary:
                    f.write(randbytes(x))
                else:
                    f.write(randtext(x))
            f.close()
        fs = fs_pc[0]
    return 1


if __name__ == "__main__":
    if (len(sys.argv) < 4):
        print("generate_dataset.py dataset-S.cfg N_files Rand_seed Ndirs Depth")
        exit()

    infile = sys.argv[1]
    nfiles = int(sys.argv[2])
    randnew = int(sys.argv[3])
    ndirs = int(sys.argv[4])
    depth = int(sys.argv[5])
    randseed = 143

    percent = []
    fsize = []

    f = open(infile)
    fsize_percent = [[float(x) if '.' in x else int(x) for x in line.split()] for line in f]

    print("")
    print("")
    print("")
    print("")
    random.seed(randseed)
    # topdira=str(random.randrange(randmax))
    topdira = randname()
    try:
        os.mkdir(topdira)
    except:
        pass
    alldirs = make_dirtree(topdira, depth, ndirs)
    nthr = 2
    nf = nfiles / nthr
    randseed = randnew
    randseed = randseed + 110
    lock = Lock()
    for i in range(nthr):
        if (i == nthr - 1) & (nf < nfiles):
            nf = nfiles - (nthr - 1) * nf
        fileset = Process(target=create_fileset,
                          args=(fsize_percent, randseed, nf, alldirs, lock))
        fileset.start()
        randseed = randseed + 10
