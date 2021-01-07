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

################################################################################
# Standard libraries
################################################################################
import logging
import os
import random
from pysftp.exceptions import ConnectionException
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import AuthenticationException, SSHException
from subprocess import Popen, PIPE, CalledProcessError
from hashlib import md5
import shutil
################################################################################
# Local libraries
################################################################################
import commons.errorcodes as cterr
from commons.exceptions import CTException
from commons import commands

################################################################################
# Constants
################################################################################
log = logging.getLogger(__name__)
EXCEPTION_MSG = "*ERROR* An exception occurred in {}: {}"

################################################################################
# command execution
################################################################################
def run_remote_cmd(cmd, hostname, username, password, read_lines=True, read_nbytes=-1, 
                port=22, timeout_sec = 30, **kwargs):
    """
    Execute command on remote machine
    :return: ([stdout/stderr], True/False).
    :rtype: tuple.
    """
    try:
        if not hostname:
            raise ValueError("Missing required parameter: {}".format(hostname))
        if not username:
            raise ValueError("Missing required parameter: {}".format(username))
        if not password:
            raise ValueError("Missing required parameter: {}".format(password))
        if not cmd:
            raise ValueError("Missing required parameter: {}".format(cmd))

        log.debug("Connect details: Host:%s, user name:%s, password:%s, port:%s",
                        hostname, username, password, port=port, timeout=timeout_sec, **kwargs)
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        log.debug("Command: %s" % str(cmd))
        stdin, stdout, stderr = client.exec_command(cmd)
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
    except (SSHException, AuthenticationException, BaseException) as error:
        log.error(EXCEPTION_MSG.format(run_remote_cmd.__name__, error))
        return error, False

    return output, True

def run_local_cmd(cmd):
    """
    Execute any given command on local machine.
    :param cmd: command to be executed.
    :type cmd: str.
    :return: True/False, Success/str(err)
    :rtype: tuple.
    """
    MSG_RSA_KEY_ADDED = b"Number of key(s) added: 1"
    LCMD_NOT_FOUND = b"command not found"
    try:
        if not cmd:
            raise ValueError("Missing required parameter: {}".format(cmd))
        log.info("Command: %s", cmd)
        proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        output, error = proc.communicate()
        log.info("output = %s", str(output))
        if MSG_RSA_KEY_ADDED in output:
            return True, output
        if LCMD_NOT_FOUND in error or error:
            return False, error
    except (CalledProcessError, BaseException) as error:
        log.error(EXCEPTION_MSG.format(run_local_cmd.__name__, error))
        return False, str(error)

    return True, output

def execute_cmd(cmd, remote, *remoteargs, **remoteKwargs):
    if remote:
        result = run_remote_cmd(cmd,*remoteargs, **remoteKwargs)
    else:
        result = run_local_cmd(cmd)
    return result

def command_formatter(cmd_options, utility_path=None):
    """
    Creating command from dictionary cmd_options
    :param cmd_options: input dictionary contains command option/general_options
    :type cmd_options: dict
    :param utility_path: cli utility path for which command is being created
    :type utility_path: str
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

################################################################################
# Math operations
################################################################################

def calculate_checksum(file_path, binary_bz64=True, options=""):
    """
    Calculate MD5 checksum with/without binary coversion for a file.
    :param file_name: Name of the file with path
    :param binary_bz64: Calulate binary base64 checksum for file,
    if False it will return MD5 checksum digest
    :return: string or MD5 object
    :rtype: str
    """
    if not os.path.exists(file_path):
        return False, "Please pass proper file path"
    if binary_bz64:
        cmd = "openssl md5 -binary {} | base64".format(file_path)
    else:
        cmd = "md5sum {} {}".format(options, file_path)
    
    log.info(f"Executing cmd: {cmd}")
    result = run_local_cmd(cmd)
    log.debug("Output: {}".format(result))
    return result

def cal_percent(num1, num2):
    """
    percentage calculator to track progress
    :param num1: First number
    :param num2: second number
    :return: calculated percentage
    """
    return float(num1) / float(num2) * 100.0

################################################################################
# String operations 
################################################################################
def _format_dict(el):
    """
    Format the data in dict format
    :param el: list of string element
    :return: dict
    """
    resp_dict = {}
    list_tup = []
    for i in el:
        list_tup.append(i.split(" = "))
    for i in list_tup:
        resp_dict[i[0]] = i[1]
    return resp_dict

def format_iam_resp(self, res_msg):
    """
    Function to format IAM response which comes in string format.
    :param res_msg: bytes string of tuple
    :return: list of dict
    """
    resp = []
    res = res_msg.split("b'")[1].replace("\\n',", "").split("\\n")
    for i in res:
        new_result = i.split(',')
        result = self._format_dict(new_result)
        resp.append(result)
    return resp

def validate_output(self, output, expected_keywords):
    log.info(f"actual output {output}")
    output = [i.strip() for i in output]
    log.info("output after strip %s", output)
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

################################################################################
# File operations 
################################################################################
def is_path_exists(path):
    """
    Check if file exists locally
    :param path: Absolute path
    :return: response
    """
    return os.path.exists(path)

def open_empty_file(fpath):
    """
    Create empty file specified in path.
    :param fpath: Non-existing file path.
    :type fpath: str.
    :return: True/err.
    :rtype: bool.
    """
    try:
        with open(fpath, "w") as f_write:
            pass
    except OSError as error:
        log.error(EXCEPTION_MSG.format(open_empty_file.__name__, error))
        return False
    return True

def create_symlink(fpath,spath):
    """
    Create symlink using os.symlink specified in fpath.
    :param fpath: Existing file path.
    :type fpath: str.
    :param spath: Non-existing file path.
    :type spath: str.
    :return: True/err.
    :rtype: bool.
    """
    try:
        os.symlink(fpath, spath)
    except OSError as error:
        log.error(EXCEPTION_MSG.format(create_symlink.__name__, error))
        return False

    return True

def cleanup_directory(dpath):
    """
    Remove all files, links, directory recursively inside dpath.
    :param dpath: Absolute directory path.
    :type dpath: str.
    :return: True/False, "Success"/err
    :rtype: tuple.
    """
    for filename in os.listdir(dpath):
        file_path = os.path.join(dpath, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except OSError as error:
            log.error(EXCEPTION_MSG.format(cleanup_directory.__name__, error))
            return False
    return True

def listdir(dpath):
    """
    List directory from dpath.
    :param dpath: Directory path.
    :type dpath: str.
    :return: flist.
    :rtype: list.
    """
    try:
        flist = os.listdir(dpath)
        logging.debug("List: {}".format(flist))
    except IOError as error:
        log.error(EXCEPTION_MSG.format(listdir.__name__, error))
            
        return []

    return flist

def makedir(dpath,mode=None):
    """
    Create directory path.
    :param dpath: Directory path.
    :type dpath: str.
    :return: dpath.
    :rtype: tuple.
    """
    try:
        if mode:
            os.mkdir(path=dpath, mode=mode)
        else:
            os.mkdir(dpath)
    except IOError as error:
        log.error(EXCEPTION_MSG.format(makedir.__name__, error))
        return str(error)
    return dpath

def makedirs(dpath,mode=None):
    """
    Create directory path recursively.
    :param dpath: Directory path.
    :type dpath: str.
    :return: dpath.
    :rtype: path.
    """
    try:
        if mode:
            os.makedirs(dpath, mode)
        else:
            os.makedirs(dpath)
    except IOError as error:
        log.error(EXCEPTION_MSG.format(makedirs.__name__, error))
        return str(error)

    return dpath

def removedir(dpath):
    """
    remove empty directory.
    :param dpath: Directory path.
    :type dpath: str.
    :return: dpath
    :rtype: path.
    """
    try:
        os.rmdir(dpath)
    except IOError as error:
        log.error(EXCEPTION_MSG.format(removedir.__name__, error))
        return str(error)

    return dpath

def get_file_checksum(file_name):
    """
    This function will return checksum of file content present on the
    local server
    :param str file_name: Name of the file
    :return: (Boolean, response)
    """
    log.info("Calculating checksum of file content")
    try:
        result = md5(open(file_name, "rb").read()).hexdigest()
        return True, result
    except BaseException as error:
        log.error(EXCEPTION_MSG.format(get_file_checksum.__name__, error))
        return False, error

def create_file(file_name, count):
    cmd = commands.CREATE_FILE.format(file_name, count)
    log.debug(cmd)
    result = run_local_cmd(cmd)
    log.debug("output = {}".format(result))
    return result

def create_multiple_size_files(start_range, stop_range, file_count, folder_path, test_file_name):
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
        log.info(f"Creating {file_count} file at path {os.getcwd()}")
        for i in range(file_count):
            file_name = "{}{}".format(os.path.join(folder_path,test_file_name), i)
            create_file(file_name, random.randint(start_range, stop_range))
        list_dir = os.listdir(folder_path)
        return True, list_dir
    except BaseException as error:
        log.error(EXCEPTION_MSG.format(cleanup_directory.__name__, error))
        return False, error

def remove_file(file_path=None):
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

def split_file(file_name, size, split_count, random_part_size=False):
    """
    Creates a new file of size(count) in MB and split based on split count
    :param file_name: File name with absolute path
    :param size: Size of the file
    :param split_count: No. of parts the file needs to be split into
    :param random_part_size: True for random size parts, False for equal size parts
    :return: [{"Output":partname, "Size":partsize}]
    """

    if os.path.exists(file_name):
        log.debug("Deleting existing file: {}".format(file_name))
        remove_file(file_name)
    create_file(file_name, size)
    log.debug(
        "Created new file {} with size {} MB".format(
            file_name, size))
    dir_path = os.path.dirname(file_name)
    random.seed(1048576)
    res_d = []
    with open(file_name, "rb") as fin:
        for el in range(split_count):
            fop = "{}/{}_out{}".format(dir_path,
                                        os.path.basename(file_name), str(el))
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

def is_utility_present(self, utility_name, filepath):
    """
    This function will check utility file
    is present on specific location or not
    :return: Status(True/False) of command execution
    """
    cmd = f"ls {filepath}"
    try:
        values = run_local_cmd(cmd)
        log.info(values)
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
    """Used to take backup or restore mentioned files at the required path"""
    try:
        if action == "backup":
            log.info('Starting the backup')
            if not os.path.exists(backup_path):
                os.mkdir(backup_path)
            for files in backup_list:
                shutil.copy(files, backup_path)
                log.info(
                    "Files :{} copied successfully at path {}".format(
                        files, backup_path))
            return True, backup_list
        elif action == "restore":
            log.info('Starting the restore')
            if not os.path.exists(backup_path):
                log.info(
                    "Backup path :{}, does not exist".format(backup_path))
            else:
                os.chdir(backup_path)
                for files in backup_list:
                    file = os.path.basename(files)
                    file_path = os.path.dirname(files)
                    shutil.copy(file, file_path)
                    log.info(
                        "File :{} got copied successfully at path {}".format(
                            file, file_path))
                return True, backup_path
    except BaseException as error:
        log.error(EXCEPTION_MSG.format(backup_or_restore_files.__name__, error))
        return False, error

def is_directory_exists(path, dir_name):
    out_flag, directories = run_local_cmd(commands.LS_CMD.format(path))
    directories = (directory.split("\n")[0] for directory in directories)
    if dir_name in directories:
        return True
    else:
        return False
################################################################################
# RPM functions
################################################################################
def is_machine_clean():
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
    log.info(f"command : {rpm_cmd}")
    cmd_output = run_local_cmd(rpm_cmd)
    if cmd_output[1] != []:
        rpm_installed = True

    # Now check eos-prvsn binaries present at path
    log.info(f"command : {prvsn_dir}")
    cmd_output_1 = run_local_cmd(prvsn_dir)
    if cmd_output_1[1] != []:
        eos_prvsnr_present = True
    return rpm_installed, eos_prvsnr_present

def is_rpm_installed(expected_rpm, remote=False, *remoteargs, **remoteKwargs):
    """
    This function checks that expected rpm is currenty installed or not
    :param expected_rpm: rpm to check
    :type expected_rpm: string
    :return: True if rpm is installed, false otherwise
    :param host: Remote machine IP to connect
    :type host: str
    """
    rpm_installed = False
    cmd = commands.LST_RPM_CMD
    log.info(f"command : {cmd}")
    cmd_output = execute_cmd(cmd,remote,*remoteargs, **remoteKwargs)
    if cmd_output[1] == []:
        log.info("RPM not found")
        rpm_installed = False
        return rpm_installed, "RPM not found"
    else:
        log.info(cmd_output[1])
        rpm_list = [rpm.split("\n")[0] for rpm in cmd_output[1]]
        log.info(f"Installed RPM: {rpm_list}")
        for rpm in rpm_list:
            if rpm in expected_rpm:
                rpm_installed = True
                log.info(f"RPM {expected_rpm} already installed")
                break
        return rpm_installed, "Expected RPM installed"

def install_new_cli_rpm(rpm_link=None, remote=False,*remoteargs, **remoteKwargs ):
    cmd_output = []
    try:
        # cmd = f"yum install -y {rpm_link}"
        cmd = commands.RPM_INSTALL_CMD.format(rpm_link)
        log.info(f"command : {cmd}")
        cmd_output,cmd_flag = execute_cmd(cmd,remote,*remoteargs, **remoteKwargs)
        if cmd_flag and cmd_output != []:
            log.info("Successfully installed RPM")
        return cmd_flag, cmd_output
    except Exception as error:
        log.error(EXCEPTION_MSG.format(install_new_cli_rpm.__name__, error))
        return False, cmd_output

def list_rpms(filter_str="",remote=False,*remoteargs, **remoteKwargs):
    """
    This function lists the rpms installed on a given host and filters by given string
    :param str filter_str: string to search in rpm names for filtering results, default lists all the rpms
    :param str host: hostname or IP of the host
    :param str user: username of host
    :param str passwd: password of host
    :return: True/False, list of rpms
    :rtype: boolean, list
    """
    cmd = commands.RPM_GREP_CMD.format(filter_str)
    log.debug(f"command : {cmd}")
    resp, cmd_flag = execute_cmd(cmd,remote,*remoteargs, **remoteKwargs)
    if isinstance(resp, list):
        rpm_list = [rpm.strip("\n") for rpm in resp]
        if not rpm_list:
            return False, rpm_list
        return True, rpm_list
    else:
        return False, resp