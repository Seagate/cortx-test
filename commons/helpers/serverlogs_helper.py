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

""" This helper file is used to collect logs from Nodes for the given time stamps """

from datetime import datetime
from commons.helpers import host
from commons.utils import config_utils

fileconf_yaml = config_utils.read_yaml("config/serverlogs_helper.yaml")
fileconf = fileconf_yaml[1]

now = datetime.now()
current_time = now.strftime('%b  %#d %H:%M:%S')

class node_data:
    def __init__(self):
        self.ip = None
        self.uname = "root"
        self.passwd = "seagate"

def get_node_details(node_name):
    node_obj = node_data
    node_obj.ip = fileconf["node_ip_dict"][node_name]
    node_obj.uname = fileconf['node_username']
    node_obj.passwd = fileconf['node_password']
    return node_obj

def split_file_for_timestamp(st_time, end_time, filename, filepath, test_id):
    # split file for give time stamps and create new file with test_id
    # appended to it
    path = "{}/{}".format(filepath, filename)
    logfile = open(path, 'r')

    newname = "{}_{}".format(test_id, filename)
    newpath = "{}/{}".format(fileconf['log_destination'], newname)
    newfile = open(newpath, 'w')

    # timestamp format ('%b %#d %H:%M:%S') -> "Dec 12 16:06:01"
    st_t = st_time.split()
    en_t = end_time.split()
    start_time = "{} {} {}".format(st_t[0], st_t[1], st_t[2])
    end_time = "{} {} {}".format(en_t[0], en_t[1], en_t[2])

    for line in logfile:
        ls = line.split(' ')
        # PLEASE CHECK TIMESTAMP IN LOG FILES FIRST, For every file it might be
        # different
        timestamp = "{} {} {}".format(ls[0], ls[1], ls[2])
        if timestamp >= start_time and timestamp <= end_time:
            newfile.write(line)

    newfile.close()  # close it if done writing into it
    logfile.close()

    return newpath

def process_and_copy_file(
        st_time,
        end_time,
        file_name,
        file_path,
        localpath,
        test_id,
        sftp):
    # Copy file from node to test client
    nodepath = "{}/{}".format(file_path, file_name)
    dest_path = "{}/{}".format(fileconf['log_destination'], file_name)
    # @TODO - check sftp.get(), this call might be wrong
    sftp.get(remotepath=nodepath, localpath=dest_path)

    # 1. Fetch give file from node and Split file for given time stamp
    newfilepath = split_file_for_timestamp(
        st_time,
        end_time,
        file_name,
        fileconf['log_destination'],
        test_id)

    # 2. Copy file from node to remote server <<< @TODO need new connection
    # here !! MISSING !!!
    logserver = fileconf['logserver']
    lg_uname = fileconf['logserver_username']
    lg_passwd = fileconf['logserver_password']
    remote_path = fileconf['logserver_path']
    filename = "{}_{}".format(test_id, file_name)
    rm_path = "{}/{}".format(remote_path, filename)

    hostobj = host.Host(
        hostname=logserver,
        username=lg_uname,
        password=lg_passwd)
    hostobj.connect()
    sftp = hostobj.host_obj.open_sftp()
    sftp.put(localpath=newfilepath, remotepath=rm_path)

def collect_logs(st_time, end_time, file, node, test_id):
    # error = False #@ TODO - error handling to be done, connection retry
    # 1. Connect to node
    node_det = get_node_details(node)
    hostobj = host.Host(
        hostname=node_det.ip,
        username=node_det.uname,
        password=node_det.passwd)
    hostobj.connect()
    sftp = hostobj.host_obj.open_sftp()
    localpath = "{}_{}".format(fileconf['log_destination'], test_id)

    if file is "all":
        for fname in fileconf['file_list']:
            file_name = "{}{}".format(file, fileconf['file_exention'])
            file_path = fileconf['file_path_dict'][fname]
            process_and_copy_file(
                st_time,
                end_time,
                file_name,
                file_path,
                localpath,
                test_id,
                sftp)
    else:
        file_name = "{}{}".format(file, fileconf['file_exention'])
        file_path = fileconf['file_path_dict'][file]
        process_and_copy_file(
            st_time,
            end_time,
            file_name,
            file_path,
            localpath,
            test_id,
            sftp)

    # Close connection once all file transfers are done
    sftp.close

    # @TODO Error handling

def collect_logs_fromserver(
        st_time,
        test_suffix,
        end_time=current_time,
        file_type='all',
        node='all'):
    # Collect logs for all nodes

    if node is 'all':
        for node_name in fileconf['node_list']:
            response = collect_logs(
                st_time, end_time, file_type, node, test_suffix)
    # collect from one node only
    else:
        response = collect_logs(
            st_time,
            end_time,
            file_type,
            node,
            test_suffix)
