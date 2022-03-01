# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""
List of file format extensions compiled from Wikipedia.
https://en.wikipedia.org/wiki/List_of_archive_formats.
"""

blob_exts = frozenset([
    # Executables
    ".exe", ".dll", ".msi", ".com", ".drv", ".sys", ".cpl", ".ocx", ".msp",
    ".ipa", ".jar", ".apk",

    # Images
    ".gif", ".jpg", ".bmp", ".png", ".tif", ".jpe", ".raw", ".pic", ".pct",
    ".pxr", ".sct", ".ico", ".psd", ".CR2", ".cr2", ".tga", ".tiff", ".psp", ".jpeg",

    # Video
    ".avi", ".mpg", ".mpeg", ".divx", ".rmvb", ".wmv", ".mov", ".rm", ".swf",
    ".flv", ".mkv", ".3gp", ".MTS", ".mts", ".m4v", ".arf", ".trec",

    # Audio
    ".ogg", ".mp3", ".wav", ".flac", ".mpc", ".au", ".aiff", ".aac", ".mp4",
    ".m4a", ".ra", ".ape", ".aif",

    # Compressed
    ".zip", ".rar", ".gz", ".tgz", ".7z", ".tbz",
    ".bz2", ".war", ".lz", ".xz", ".deb", ".ipsw",

    # Contacts
    ".vcf"
])

#
# Treat the following as completely over-written file formats
immutable_exts = blob_exts | frozenset([
    # Office
    ".doc", ".ppt", ".xls", ".docx", ".docm", ".xlsx", ".xlsm", ".xts",
    ".xltm", ".pptx", ".pptm", ".odt", ".odb", ".ods", ".odp", ".odg", ".odc",
    ".odf", ".odi", ".odm", ".ott", ".ots", ".otp", ".otg", ".otc", ".otf",
    ".oti", ".oth", ".vssx", ".vssm", ".vstx", ".vstm", ".vsl", ".dot", ".dotm",
    ".xlt", ".pot", ".potx", ".potm", ".one", ".xsn", ".mpt", ".pub", ".vdx", ".vtx",
    ".vsx", ".sldm", ".sldx", ".onetoc", ".slk", ".dif", ".msg", ".oft", ".ppam",
    ".ppsm", ".thmx", ".xps", ".rtf", ".onetoc2",

    # PDF
    ".pdf",

    # HTML
    ".html", ".htm",

    # misc
    ".log", ".idx",

    # disk images
    ".iso", ".img", ".dmg",

    # oracle/java, .hprof -> java heap dump.
    ".pack", ".hprof",
    ".json",

    # True type fonts.
    ".ttf",

    # Lexmark firmware.
    ".ppn",

    # svn source base copy.
    ".svn-base",

    # keynote presentation.
    ".key",

    # Misc.
    ".tar", ".cvs"
])

struct_exts = frozenset([
    # Databases
    ".db", ".dbf", ".sql", ".accdb", ".mdb", ".myd",
])

#
# Set of extensions containing compressed data.
compressed_exts = frozenset([
    # List of archive formats extensions. Compiled from
    # https://en.wikipedia.org/wiki/List_of_archive_formats
    '.a', '.ar', '.cpio', '.shar', '.lbr', '.iso', '.mar',
    '.sbx', '.gz', '.bz2', '.zip', '.lz', '.lzma', '.lzo', '.rz', '.sfark',
    '.sz', '.xz', '.z', '.7z', '.s7z', '.ace', '.afa', '.alz',
    '.apk', '.arc', '.arj', '.b1', '.b6z', '.ba', '.bh', '.cab', '.car',
    '.cfs', '.cpt', '.dar', '.dd', '.dgc', '.dmg', '.ear', '.gca', '.ha',
    '.hki', '.ice', '.jar', '.kgb', '.lzh', '.lha', '.lzx', '.pak', '.partimg',
    '.paq6', '.paq7', '.paq8', '.pea', '.pim', '.pit', '.qda', '.rar', '.rk',
    '.sda', '.sea', '.sen', '.sfx', '.shk', '.sit', '.sitx', '.sqx', '.tgz',
    '.tbz2', '.lzma', '.tlz', '.xz', '.txz',

    # List of audio format extensions. Compiled from
    # https://en.wikipedia.org/wiki/Audio_file_format
    '.3gp', '.aa', '.aac', '.aax', '.act', '.amr', '.ape', '.awb', '.dct',
    '.dss', '.dvf', '.flac', '.gsm', '.iklax', '.ivs', '.m4a', '.m4b', '.m4p',
    '.mmf', '.mp3', '.mpc', '.msv', '.ogg', '.oga', '.mogg', '.opus', '.ra',
    '.rm', '.sln', '.tta', '.vox', '.wma', '.wv', '.webm', '.8svx',

    # List of video format extensions. Compiled from
    # https://en.wikipedia.org/wiki/Video_file_format
    '.mkv', '.flv', '.vob', '.ogv', '.drc', '.gif', '.gifv', '.mng', '.avi',
    '.mov', '.qt', '.wmv', '.yuv', '.rmvb', '.asf', '.amv', '.mp4', '.m4p',
    '.m4v', '.mpg', '.mp2', '.mpeg', '.mpe', '.mpv', '.m2v', '.svi', '.3g2',
    '.mxf', '.roq', '.nsv', '.f4v', '.f4p', '.f4a', '.f4b',

    # List of image format extensions. Compiled from
    # https://en.wikipedia.org/wiki/Image_file_formats
    '.jpeg', '.jpg', '.jpe', '.tiff', '.tif', '.png', '.cd5', '.img', '.cpt',
    '.psd', '.psp', '.pspimage', '.tga', '.yuv', '.thm', '.srt', '.swf',
    '.pdf', '.ps'])

all_extensions = immutable_exts | compressed_exts
extensions_count = len(all_extensions)

if __name__ == "__main__":
    print(all_extensions)
