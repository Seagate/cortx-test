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
#"""This Utility function is for downloading files from required sources."""
import os
import requests


def download_file(file_download_path, file_save_path, file_name="temp"):
    """
    This function is used to download file update
    :param file_download_path: File path from where the file for SW update can be downloaded
    :param file_save_path:  The file path to be saved
    :param file_name:  The file name to be downloaded
    :return:  File path
    """
    file_save_path = str(file_save_path)+os.sep+str(file_name)
    # Streaming file to download path
    with requests.get(file_download_path, stream=True) as result:
        result.raise_for_status()
        with open(file_save_path, 'wb') as file_data:
            for chunk in result.iter_content(chunk_size=10240):
                file_data.write(chunk)
    return file_save_path
