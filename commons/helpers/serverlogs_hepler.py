#!/usr/bin/python
""" This helper file is used to collect logs from Nodes for the given time stamps """

from datetime import datetime
from commons.helpers import node_helper

utils_obj = node_helper.Utility()

now = datetime.now()
current_time = now.strftime('%b  %#d %H:%M:%S')

node_list = ['node1', 'node2', 'node3', 'node4']
file_list = ['s3', 'motr', 'ras', 'ha', 'prov']

log_destination = "/root/mahesh/temp"
file_exention = ".log"
filenameformat = "cortx_"  # TODO change this path accordingly

# @TODO change this path accordingly
file_path_dict = {"s3": "/home/s3path", "motr": "/root/mahesh", "ras": "/home/raspath", "ha": "/home/hapath",
                  "prov": "/home/provpath"}
node_ip_dict = {"node1": "10.237.65.202", "node1": "10.237.65.160"}

class node_data:  # @TODO - visit this again
    def __init__(self):
        self.ip = None
        self.uname = "root"
        self.passwd = "seagate"

def get_node_details(node_name):  # @TODO- visit again
    node_obj = node_data
    node_obj.ip = node_ip_dict.get(node_name)
    node_obj.uname = "root"
    node_obj.passwd = "seagate"
    return node_obj

def split_file_for_timestamp(st_time, end_time, filename, filepath, test_id):
    # split file for give time stamps and create new file with test_id appended to it
    path = "{}/{}".format(filepath, filename)
    logfile = open(path, 'r')

    newname = "{}_{}".format(test_id, filename)
    newpath = "{}/{}".format(log_destination, newname)
    newfile = open(newpath, 'w')

    # timestamp format ('%b %#d %H:%M:%S') -> "Dec 12 16:06:01"
    st_t = st_time.split()
    en_t = end_time.split()
    start_time = "{} {} {}".format(st_t[0], st_t[1], st_t[2])
    end_time = "{} {} {}".format(en_t[0], en_t[1], en_t[2])

    for line in logfile:
        ls = line.split(' ')
        # PLEASE CHECK TIMESTAMP IN LOG FILES FIRST, For every file it might be different
        timestamp = "{} {} {}".format(ls[0], ls[1], ls[2])
        if timestamp >= start_time and timestamp <= end_time:
            newfile.write(line)

    newfile.close()  # close it if done writing into it

    return newpath

def process_and_copy_file(st_time, end_time, file_name, file_path, localpath, test_id, sftp):
    # Copy file from node to test client
    nodepath = "{}/{}".format(file_path, file_name)
    dest_path = "{}/{}".format(log_destination, file_name)
    sftp.put(localpath=nodepath, remotepath=dest_path)  # @TODO - check sftp.get(), this call might be wrong

    # 1. Fetch give file from node and Split file for given time stamp
    newfilepath = split_file_for_timestamp(st_time, end_time, file_name, log_destination, test_id)

    # 2. Copy file from node to remote server <<< @TODO need new connection here !! MISSING !!!
    logserver = "10.237.65.125"
    connect_obj = utils_obj.connect(logserver,
                                    username="root",
                                    password="seagate",
                                    shell=False)
    sftp = connect_obj.open_sftp()
    remote_path = "/root/mahesh/temp"
    filename = "{}_{}".format(test_id, file_name)
    rm_path = "{}/{}".format(remote_path, filename)
    sftp.put(localpath=newfilepath, remotepath=rm_path)

def collect_logs(st_time, end_time, file, node, test_id):
    # error = False #@ TODO - error handling to be done, connection retry
    # 1. Connect to node
    node_det = get_node_details(node)
    connect_obj = utils_obj.connect(node_det.ip,
                                    username=node_det.uname,
                                    password=node_det.passwd,
                                    shell=False)
    sftp = connect_obj.open_sftp()
    localpath = "{}_{}".format(log_destination, test_id)

    if file is "all":
        for fname in file_list:
            file_name = "{}{}{}".format(filenameformat, fname, file_exention)
            file_path = file_path_dict.get("{}".format(fname))
            process_and_copy_file(st_time, end_time, file_name, file_path, localpath, test_id, sftp)
    else:
        file_name = "{}{}{}".format(filenameformat, file, file_exention)
        file_path = file_path_dict.get("{}".format(file))
        process_and_copy_file(st_time, end_time, file_name, file_path, localpath, test_id, sftp)

    # Close connection once all file transfers are done
    sftp.close

    # Error handling
    # if error:
    # log.warn("Error: Could not collect logs from node {0} for file {1}", node, file, test_id)
    # else:
    # log.info("Success: Logs Collected from node {0} for file {1}", node, file, test_id)

def collect_logs_fromserver(st_time, test_suffix, end_time=current_time, file_type='all', node='all'):
    # Collect logs for all nodes
    if node is 'all':
        for node_name in node_list:
            response = collect_logs(st_time, end_time, file_type, node, test_suffix)
    # collect from one node only
    else:
        response = collect_logs(st_time, end_time, file_type, node, test_suffix)

