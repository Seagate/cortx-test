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

import logging
import os
import random
from typing import Union, Tuple, List
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import AuthenticationException, SSHException
from subprocess import Popen, PIPE, CalledProcessError
from hashlib import md5
import shutil
from commons import commands

log = logging.getLogger(__name__)
EXCEPTION_MSG = "*ERROR* An exception occurred in {}: {}"

def run_remote_cmd(cmd:str, hostname:str, username:str, password:str, read_lines:bool=False, 
                    read_nbytes:int=-1, timeout_sec:int=30, **kwargs)->str:
    """
    Execute command on remote machine
    :return: stdout
    """
    if not hostname:
        raise ValueError("Missing required parameter: {}".format(hostname))
    if not username:
        raise ValueError("Missing required parameter: {}".format(username))
    if not password:
        raise ValueError("Missing required parameter: {}".format(password))
    if not cmd:
        raise ValueError("Missing required parameter: {}".format(cmd))

    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    log.debug("Command: %s" % str(cmd))
    client.connect(hostname,username=username, password=password, timeout=timeout_sec)
    _, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    if read_lines:
        output = stdout.readlines()
        output = [r.strip().strip("\n").strip() for r in output]
        log.debug("Result: %s" % str(output))
        error = stderr.readlines()
        error = [r.strip().strip("\n").strip() for r in error]
        log.debug("Error: %s" % str(error))
    else:
        output = stdout.read(read_nbytes)
        error = stderr.read()
    log.debug(exit_status)
    if exit_status != 0:
        if error:
            raise IOError(error)
        raise IOError(output)
    client.close()
    if error:
        raise IOError(error)
    return output

def run_local_cmd(cmd:str)->str:
    """
    Execute any given command on local machine.
    :param cmd: command to be executed.
    :return: stdout 
    """
    msg_rsa_key_added = b"Number of key(s) added: 1"
    lcmd_not_found = b"command not found"
    if not cmd:
        raise ValueError("Missing required parameter: {}".format(cmd))
    log.debug("Command: %s", cmd)
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, error = proc.communicate()
    log.debug("output = %s", str(output))
    if msg_rsa_key_added in output:
        return True, output
    if lcmd_not_found in error or error:
        raise IOError(error)
    return output

def execute_cmd(cmd:str, remote:bool, *remoteargs, **remoteKwargs)->str:
    """Execute command on local / remote machine based on remote flag
    :param cmd: cmd to be executed
    :param remote: if True executes on remote machine
    """    
    if remote:
        result = run_remote_cmd(cmd,*remoteargs, **remoteKwargs)
    else:
        result = run_local_cmd(cmd)
    return result

def command_formatter(cmd_options:dict, utility_path:str=None)->str:
    """
    TODO: If this function is not being used, we can delete it later.
    Creating command from dictionary cmd_options
    :param cmd_options: input dictionary contains command option/general_options
    :param utility_path: cli utility path for which command is being created
    :return: actual command that is going to execute for utility
    """
    cmd_elements = []
    # utility path only for cli utilities
    if utility_path:
        cmd_elements.append(utility_path)
    # Positional argument is mandatory
    if 'positional_argument' in cmd_options:
        cmd_elements.append(cmd_options['positional_argument'])
    if 'options' in cmd_options:
        for argument in cmd_options['options']:
            arg_val = cmd_options['options'][argument]
            if arg_val is None:
                arg_str = argument
            else:
                arg_str = argument + " " + arg_val
            cmd_elements.append(arg_str)
    if 'general_options' in cmd_options:
        for argument in cmd_options['general_options']:
            arg_val = cmd_options['general_options'][argument]
            if arg_val is None:
                arg_str = argument
            else:
                arg_str = argument + " " + arg_val
            cmd_elements.append(arg_str)
    if 'teardown' in cmd_options:
        cmd_elements.append("salt")
        if '--local' in cmd_options['teardown']:
            cmd_elements.append("--local")
        else:
            cmd_elements.append("'*'")
        # "all-at-time" is to execute teardown services all at a time
        if 'all-at-time' in cmd_options['teardown']['services']:
            cmd_elements.append("state.apply components.teardown")
        # "one-by-one" is to execute teardown services individually
        elif 'one-by-one' in cmd_options['teardown']['services']:
            cmd_elements.append("state.apply components.%s.teardown")

    cmd = " ".join(cmd_elements)
    return cmd

def calculate_checksum(file_path:str, binary_bz64:bool=True, options="")->str:
    """
    Calculate MD5 checksum with/without binary coversion for a file.
    :param filename: Name of the file with path
    :param binary_bz64: Calulate binary base64 checksum for file,
    if False it will return MD5 checksum digest
    :return: string or MD5 object
    """
    if not os.path.exists(file_path):
        return False, "Please pass proper file path"
    if binary_bz64:
        cmd = "openssl md5 -binary {} | base64".format(file_path)
    else:
        cmd = "md5sum {} {}".format(options, file_path)
    
    log.debug(f"Executing cmd: {cmd}")
    result = run_local_cmd(cmd)
    log.debug("Output: {}".format(result))
    return result

def cal_percent(num1:float, num2:float)->float:
    """
    percentage calculator to track progress
    :param num1: First number
    :param num2: second number
    :return: calculated percentage
    """
    return float(num1) / float(num2) * 100.0

def _format_dict(el:list)->dict:
    """
    TODO remove later as IAM is not supported
    Format the data in dict format
    :param el: list of string element
    """
    resp_dict = {}
    list_tup = []
    for i in el:
        list_tup.append(i.split(" = "))
    for i in list_tup:
        resp_dict[i[0]] = i[1]
    return resp_dict

def format_iam_resp(res_msg:str)->list:
    """
    #TODO remove later as IAM is not supported
    Function to format IAM response which comes in string format.
    :param res_msg: bytes string of tuple
    :return: list of dict
    """
    resp = []
    res = res_msg.split("b'")[1].replace("\\n',", "").split("\\n")
    for i in res:
        new_result = i.split(',')
        result = _format_dict(new_result)
        resp.append(result)
    return resp

def validate_output(output:str, expected_keywords:str):
    log.debug(f"actual output {output}")
    output = [i.strip() for i in output]
    log.debug("output after strip %s", output)
    validation_steps = dict()
    for ele in expected_keywords:
        validation_steps[ele] = False
    for line in output:
        for out in validation_steps:
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            if out in line:
                validation_steps[out] = True
    retval = (
        False not in list(
            validation_steps.values()),
        'validation failed')
    return retval

def open_empty_file(fpath:str)->bool:
    """
    Create empty file specified in path.
    :param fpath: Non-existing file path.
    :return: True/False
    """
    with open(fpath, "w") as f_write:
        pass
    return os.path.exists(fpath)

def create_symlink(fpath:str, spath:str)->bool:
    """
    Create symlink using os.symlink specified in fpath.
    :param fpath: Existing file path.
    :param spath: Non-existing file path.
    :return: True/err.
    """
    try:
        os.symlink(fpath, spath)
    except OSError as error:
        log.error(EXCEPTION_MSG.format(create_symlink.__name__, error))
        return False
    return True

def cleanup_dir(dpath:str)->bool:
    """
    Remove all files, links, directory recursively inside dpath.
    :param dpath: Absolute directory path.
    :return: True/False
    """
    for filename in os.listdir(dpath):
        file_path = os.path.join(dpath, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except OSError as error:
            log.error(EXCEPTION_MSG.format(cleanup_dir.__name__, error))
            return False
    return True

def list_dir(dpath:str)->list:
    """
    List directory from dpath.
    :param dpath: Directory path.
    """
    try:
        flist = os.listdir(dpath)
        logging.debug("List: {}".format(flist))
    except IOError as error:
        log.error(EXCEPTION_MSG.format(list_dir.__name__, error))
        return []
    return flist

def make_dir(dpath:str,mode:int=None):
    """
    Create directory path.
    :param dpath: Directory path.
    :type dpath: str.
    :return: dpath.
    :rtype: tuple.
    """
    if mode:
        os.mkdir(path=dpath, mode=mode)
    else:
        os.mkdir(dpath)
    return os.path.exists(dpath)

def make_dirs(dpath:str,mode:int=None):
    """
    Create directory path recursively.
    :param dpath: Directory path.
    :return: dpath.
    """
    try:
        if mode:
            os.makedirs(dpath, mode)
        else:
            os.makedirs(dpath)
    except IOError as error:
        log.error(EXCEPTION_MSG.format(make_dirs.__name__, error))
        return str(error)
    return dpath

def remove_dir(dpath:str)->str:
    """
    remove empty directory.
    :param dpath: Directory path.
    :return: dpath
    """
    os.rmdir(dpath)
    return os.path.exists(dpath)

def get_file_checksum(filename:str):
    """
    This function will return checksum of file content present on the
    local server
    :param  filename: Name of the file
    :return: (Boolean, response)
    """
    log.debug("Calculating checksum of file content")
    try:
        result = md5(open(filename, "rb").read()).hexdigest()
        return True, result
    except BaseException as error:
        log.error(EXCEPTION_MSG.format(get_file_checksum.__name__, error))
        return False, error

def create_file(filename:str, count:int):
    cmd = commands.CREATE_FILE.format(filename, count)
    log.debug(cmd)
    result = run_local_cmd(cmd)
    log.debug("output = {}".format(result))
    return result

def create_multiple_size_files(start_range, stop_range, file_count, folder_path, test_filename):
    """
    Creating multiple random size files in a folder
    :param start_range: Start range of the file
    :param stop_range: Stop range of the file
    :param file_count: No of files
    :param folder_path: folder path at which file will be created
    :return: folder list
    """
    if not os.path.exists(folder_path):
        log.warning(f"{folder_path} doesnt exist creating new one")
        os.mkdir(folder_path)
    try:
        os.chdir(folder_path)
        log.debug(f"Creating {file_count} file at path {os.getcwd()}")
        for i in range(file_count):
            filename = "{}{}".format(os.path.join(folder_path,test_filename), i)
            create_file(filename, random.randint(start_range, stop_range))
        list_dir = os.listdir(folder_path)
        return True, list_dir
    except BaseException as error:
        log.error(EXCEPTION_MSG.format(create_multiple_size_files.__name__, error))
        return False, error

def remove_file(file_path:str=None):
    """
    This function is used to remove file at specified path
    :param file_path: Path of file to be deleted
    :return: (Boolean, Response)
    """
    try:
        os.remove(file_path)
        return True, "Success"
    except Exception as error:
        log.error(EXCEPTION_MSG.format(remove_file.__name__, error))
        return False, error

def split_file(filename, size, split_count, random_part_size=False):
    """
    Creates a new file of size(count) in MB and split based on split count
    :param filename: File name with absolute path
    :param size: Size of the file
    :param split_count: No. of parts the file needs to be split into
    :param random_part_size: True for random size parts, False for equal size parts
    :return: [{"Output":partname, "Size":partsize}]
    """

    if os.path.exists(filename):
        log.debug("Deleting existing file: {}".format(filename))
        remove_file(filename)
    create_file(filename, size)
    log.debug(
        "Created new file {} with size {} MB".format(
            filename, size))
    dir_path = os.path.dirname(filename)
    random.seed(1048576)
    res_d = []
    with open(filename, "rb") as fin:
        for el in range(split_count):
            fop = "{}/{}_out{}".format(dir_path,
                                        os.path.basename(filename), str(el))
            if random_part_size:
                read_bytes = random.randint(
                    1048576 * size // 10, 1048576 * size)
            else:
                read_bytes = (1048576 * size // split_count)
            with open(fop, 'wb') as split_fin:
                split_fin.write(fin.read(read_bytes))
                res_d.append({"Output": fop, "Size": os.stat(fop).st_size})
    log.debug(res_d)
    return res_d

def is_utility_present(utility_name:str, filepath:str)->bool:
    """
    This function will check utility file
    is present on specific location or not
    :return: Status(True/False) of command execution
    """
    cmd = f"ls {filepath}"
    try:
        values = run_local_cmd(cmd)
        log.debug(values)
        if values[0]:
            for val in values[1]:
                if utility_name == val.split("\n")[0]:
                    return True
        return False
    except BaseException as error:
        log.error(EXCEPTION_MSG.format(is_utility_present.__name__, error))
        return False

def backup_or_restore_files(action,
                            backup_path,
                            backup_list):
    """Used to take backup or restore mentioned files at the required path
    """
    try:
        if action == "backup":
            log.debug('Starting the backup')
            if not os.path.exists(backup_path):
                os.mkdir(backup_path)
            for files in backup_list:
                shutil.copy(files, backup_path)
                log.debug(
                    "Files :{} copied successfully at path {}".format(
                        files, backup_path))
            return True, backup_list
        elif action == "restore":
            log.debug('Starting the restore')
            if not os.path.exists(backup_path):
                log.debug(
                    "Backup path :{}, does not exist".format(backup_path))
            else:
                os.chdir(backup_path)
                for files in backup_list:
                    file = os.path.basename(files)
                    file_path = os.path.dirname(files)
                    shutil.copy(file, file_path)
                    log.debug(
                        "File :{} got copied successfully at path {}".format(
                            file, file_path))
                return True, backup_path
    except BaseException as error:
        log.error(EXCEPTION_MSG.format(backup_or_restore_files.__name__, error))
        return False, error

def is_dir_exists(path:str, dir_name:str)->bool:
    directories = run_local_cmd(commands.LS_CMD.format(path))
    directories = (directory.split("\n")[0] for directory in directories)
    if dir_name in directories:
        return True
    else:
        return False

def is_machine_clean()->Tuple[bool,bool]:
    """
    This function checks that any rpm is installed on machine and
    will check for eos-prvsnr binaries present at /opt/seagate/ path
    ex -
    rpm_cmd = "rpm -qa | grep eos-prvsnr"
    bin_cmd = "ls /opt/seagate/"
    :return: boolean values for both scenarioes
    """
    rpm_installed = False
    eos_prvsnr_present = False

    # Check any RPM is being installed on machine
    rpm_cmd = commands.LST_RPM_CMD
    prvsn_dir = commands.LST_PRVSN_DIR
    log.debug(f"command : {rpm_cmd}")
    cmd_output = run_local_cmd(rpm_cmd)
    if cmd_output[1] != []:
        rpm_installed = True

    # Now check eos-prvsn binaries present at path
    log.debug(f"command : {prvsn_dir}")
    cmd_output_1 = run_local_cmd(prvsn_dir)
    if cmd_output_1[1] != []:
        eos_prvsnr_present = True
    return rpm_installed, eos_prvsnr_present

def is_rpm_installed(expected_rpm:str, remote:bool=False, *remoteargs, **remoteKwargs)->bool:
    """
    This function checks that expected rpm is currenty installed or not
    :param expected_rpm: rpm to check
    :return: True if rpm is installed, false otherwise    """
    rpm_installed = False
    cmd = commands.LST_RPM_CMD
    log.debug(f"command : {cmd}")
    cmd_output = execute_cmd(cmd,remote,*remoteargs, **remoteKwargs)
    if cmd_output[1] == []:
        log.debug("RPM not found")
        rpm_installed = False
        return rpm_installed, "RPM not found"
    else:
        log.debug(cmd_output[1])
        rpm_list = [rpm.split("\n")[0] for rpm in cmd_output[1]]
        log.debug(f"Installed RPM: {rpm_list}")
        for rpm in rpm_list:
            if rpm in expected_rpm:
                rpm_installed = True
                log.debug(f"RPM {expected_rpm} already installed")
                break
        return rpm_installed, "Expected RPM installed"

def install_new_cli_rpm(rpm_link=None, remote=False,*remoteargs, **remoteKwargs ):
    cmd_output = []
    # cmd = f"yum install -y {rpm_link}"
    cmd = commands.RPM_INSTALL_CMD.format(rpm_link)
    log.debug(f"command : {cmd}")
    cmd_output = execute_cmd(cmd,remote,*remoteargs, **remoteKwargs)
    if cmd_output != []:
        log.debug("Successfully installed RPM")
    return cmd_output

def list_rpms(filter_str="",remote=False,*remoteargs, **remoteKwargs)->Tuple[bool,list]:
    """
    This function lists the rpms installed on a given host and filters by given string
    :param str filter_str: string to search in rpm names for filtering results, default lists all the rpms
    :return: True/False, list of rpms
    """
    cmd = commands.RPM_GREP_CMD.format(filter_str)
    log.debug(f"command : {cmd}")
    resp  = execute_cmd(cmd,remote,*remoteargs, **remoteKwargs)
    if isinstance(resp, list):
        rpm_list = [rpm.strip("\n") for rpm in resp]
        if not rpm_list:
            return False, rpm_list
        return True, rpm_list
    else:
        return False, resp

def check_ping(host:str)->bool:
    """
    This function will send ping to the given host
    :param str host: Host to whom ping to be sent
    :return: True/ False
    """
    response = os.system("ping -c 1 {}".format(host))
    return (response == 0)

def pgrep(process:str):
    """
    Function to get process ID using pgrep cmd.
    :param process: Name of the process
    :return: response
    """
    response = run_local_cmd(commands.PGREP_CMD.format(process))
    return response

def get_disk_usage(path:str)->str:
    """
    This function will return disk usage associated with given path.
    :param path: Path to retrieve disk usage
    :return: Disk usage of given path
    """
    log.debug("Running local disk usage cmd.")
    stats = os.statvfs(path)
    f_blocks, f_frsize, f_bfree = stats.f_blocks, stats.f_frsize, stats.f_bfree
    total = (f_blocks * f_frsize)
    used = (f_blocks - f_bfree) * f_frsize
    result = format((float(used) / total) * 100, ".1f")
    return result