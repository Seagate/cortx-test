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
"""aws configuration module for containerised client"""

import argparse

parser = argparse.ArgumentParser(description='Update the aws credentials file')
parser.add_argument('--access_key',
                    help='aws access key Id')
parser.add_argument('--secret_key',
                    help='aws secret key')
args = parser.parse_args()

ACCESS_KEY = args.access_key
SECRET_KEY = args.secret_key

lines = ['[default]\n', 'aws_access_key_id = {}\n'.format(ACCESS_KEY),
         'aws_secret_access_key = {}\n'.format(SECRET_KEY)]

f = open('/root/.aws/credentials', 'w')
f.writelines(lines)
f.close()

print('Added Credentials')
