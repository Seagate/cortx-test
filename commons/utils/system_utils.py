#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Module to maintain system utils."""

import logging
import os
import secrets
import sys
import time
import platform
import shutil
import socket
import builtins
import errno
import string
import glob
from typing import Tuple
from subprocess import Popen, PIPE
from hashlib import md5
from pathlib import Path
from botocore.response import StreamingBody
from paramiko import SSHClient, AutoAddPolicy
from commons import commands
from commons import params
from commons.constants import AWS_CLI_ERROR

if sys.platform == 'win32':
    try:
        import msvcrt
    except ImportError:
        MSVCRT = None
if sys.platform in ['linux', 'linux2']:
    try:
        import fcntl
    except ImportError:
        FCNTL = None

LOGGER = logging.getLogger(__name__)

DNS_RR_COUNTER = 0


def run_remote_cmd(cmd: str, hostname: str, username: str, password: str,
                   **kwargs) -> tuple:
    """
    Execute command on remote machine.
    :return: stdout
    """
    LOGGER.info("Host: %s, User: %s, Password: %s", hostname, username, password)
    read_lines = kwargs.get("read_lines", False)
    read_nbytes = kwargs.get("read_nbytes", -1)
    timeout_sec = kwargs.get("timeout_sec", 30)
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    LOGGER.debug("Command: %s", str(cmd))
    client.connect(hostname, username=username, password=password, timeout=timeout_sec)
    _, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    if read_lines:
        output = stdout.readlines()
        output = [r.strip().strip("\n").strip() for r in output]
        if output and "hctl status" not in cmd and "pcs status" not in cmd:
            LOGGER.debug("Result: %s", str(output))
        error = stderr.readlines()
        error = [r.strip().strip("\n").strip() for r in error]
        if error:
            LOGGER.debug("Error: %s", str(error))
    else:
        output = stdout.read(read_nbytes)
        if output and "hctl status" not in cmd and "pcs status" not in cmd:
            LOGGER.debug("Result: %s", str(output))
        error = stderr.read()
        if error:
            LOGGER.debug("Error: %s", str(error))
    LOGGER.debug(exit_status)
    if exit_status != 0:
        if error:
            return False, error
        return False, output
    client.close()
    if error:
        return False, error

    return True, output


def run_remote_cmd_wo_decision(cmd: str, hostname: str, username: str, password: str,
                               **kwargs) -> tuple:
    """
    Execute command on remote machine.
    :return: stdout, stderr, status
    :Need this command because motr api send output on stderr
    """
    LOGGER.info("Host: %s, User: %s, Password: %s", hostname, username, password)
    read_lines = kwargs.get("read_lines", False)
    read_nbytes = kwargs.get("read_nbytes", -1)
    timeout_sec = kwargs.get("timeout_sec", 30)
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    LOGGER.debug("Command: %s", str(cmd))
    client.connect(hostname, username=username, password=password, timeout=timeout_sec)
    _, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    if read_lines:
        output = stdout.readlines()
        output = [r.strip().strip("\n").strip() for r in output]
        if output and "hctl status" not in cmd and "pcs status" not in cmd:
            LOGGER.debug("Result: %s", str(output))
        error = stderr.readlines()
        error = [r.strip().strip("\n").strip() for r in error]
        if error:
            LOGGER.debug("Error: %s", str(error))
    else:
        output = stdout.read(read_nbytes)
        if output and "hctl status" not in cmd and "pcs status" not in cmd:
            LOGGER.debug("Result: %s", str(output))
        error = stderr.read()
        if error:
            LOGGER.debug("Error: %s", str(error))
    client.close()
    return output, error, exit_status


def run_local_cmd(cmd: str = None, flg: bool = False, chk_stderr: bool = False) -> tuple:
    """
    Execute any given command on local machine(Windows, Linux)
    :param cmd: command to be executed
    :param flg: To get str(proc.communicate())
    :param chk_stderr: Check if stderr is none.
    :return: bool, response.
    """
    if not cmd:
        raise ValueError("Missing required parameter: {}".format(cmd))
    LOGGER.debug("Command: %s", cmd)
    proc = None
    try:
        proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)  # nosec (B603)
        output, error = proc.communicate()
        LOGGER.debug("output = %s", str(output))
        LOGGER.debug("error = %s", str(error))
        if flg:
            return True, str((output, error))
        if chk_stderr:
            if error and check_aws_cli_error(str(error)):
                return False, str(error)
            return True, str(output)
        if proc.returncode != 0:
            return False, str(error)
        if b"Number of key(s) added: 1" in output:
            return True, str(output)
        if b"command not found" in error or \
                b"not recognized as an internal or external command" in error or error:
            return False, str(error)

        return True, str(output)
    except RuntimeError as ex:
        LOGGER.exception(ex)
        return False, ex
    finally:
        if proc:
            proc.terminate()


def check_aws_cli_error(str_error: str):
    """Validate error string from aws cli command."""
    err_check = True
    # InsecureRequestWarning: Unverified HTTPS request is being made to host 'public data ip'.
    # Adding certificate verification is strongly advised.
    if "InsecureRequestWarning" in str_error or "WARNING: " in str_error:
        err_check = False
    for error in AWS_CLI_ERROR:
        if error in str_error:
            err_check = True
            break

    return err_check


def execute_cmd(cmd: str, *remoteargs, remote: bool = False, **remotekwargs) -> tuple:
    """Execute command on local / remote machine based on remote flag
    :param cmd: cmd to be executed
    :param remote: if True executes on remote machine
    """
    if remote:
        result = run_remote_cmd(cmd, *remoteargs, **remotekwargs)
    else:
        result = run_local_cmd(cmd)

    return result


def command_formatter(cmd_options: dict, utility_path: str = None) -> str:
    """
    TODO: If this function is not being used, we can delete it later.
    Creating command from dictionary cmd_options
    :param cmd_options: input dictionary contains command option/general_options
    :param utility_path: cli utility path for which command is being created
    :return: actual command that is going to execute for utility
    """
    cmd_elements = list()
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


def filter_bin_md5(file_checksum):
    """
    Function to clean binary md5 response
    :param file_checksum: encoded binary md5 data with newline char
    :return: filter binary md5 data
    """
    LOGGER.debug("Actual MD5 %s", file_checksum)
    if "\\n" in file_checksum[2:-1]:
        bin_checksum = file_checksum[2:-1].replace("\\n", "")
    elif "\n" in file_checksum[2:-1]:
        bin_checksum = file_checksum[2:-1].replace("\n", "")
    else:
        bin_checksum = file_checksum[2:-1]
    LOGGER.debug("Filter MD5 %s", bin_checksum)

    return bin_checksum


def calculate_checksum(file_path: str, binary_bz64: bool = True, options: str = "", **kwargs)\
        -> tuple:
    """
    Calculate MD5 checksum with/without binary conversion for a file
    :param file_path: Name of the file with path
    :param binary_bz64: Calculate binary base64 checksum for file,
    if False it will return MD5 checksum digest
    :param options: option for md5sum tool
    :keyword filter_resp: filter md5 checksum cmd response True/False
    # :param hash_algo: calculate checksum for given hash algo
    :return: string or MD5 object
    """
    hash_algo = kwargs.get("hash_algo", "md5")
    if not os.path.exists(file_path):
        return False, "Please pass proper file path"
    if hash_algo == "md5":
        if binary_bz64:
            cmd = "openssl md5 -binary {} | base64".format(file_path)
        else:
            cmd = "md5sum {} {}".format(options, file_path)
    if hash_algo == "SHA-1":
        cmd = "sha1sum {}".format(file_path)
    if hash_algo == "SHA-224":
        cmd = "sha224sum {}".format(file_path)
    if hash_algo == "SHA-256":
        cmd = "sha256sum {}".format(file_path)
    if hash_algo == "SHA-384":
        cmd = "sha384sum {}".format(file_path)
    if hash_algo == "SHA-512":
        cmd = "sha512sum {}".format(file_path)

    LOGGER.debug("Executing cmd: %s", cmd)
    result = run_local_cmd(cmd)
    LOGGER.debug("Output: %s", str(result))
    if kwargs.get("filter_resp", None) and binary_bz64:
        result = (result[0], filter_bin_md5(result[1]))
    return result


def calc_checksum(object_ref: object, hash_algo: str = 'md5'):
    """
    Calculate checksum of file or stream
    :param object_ref: Object/File Path or byte/buffer stream
    :param hash_algo: md5 or sha1
    :return:
    """
    read_sz = 8192
    csum = None
    file_hash = md5()  # nosec
    if hash_algo != 'md5':
        raise NotImplementedError('Only md5 supported')
    if isinstance(object_ref, StreamingBody):
        chunk = object_ref.read(amt=read_sz)
        while chunk:
            file_hash.update(chunk)
            chunk = object_ref.read(amt=read_sz)
        return file_hash.hexdigest()
    if os.path.exists(object_ref):
        size = Path(object_ref).stat().st_size

        with open(object_ref, 'rb') as file_ptr:
            if size < read_sz:
                buf = file_ptr.read(size)
            else:
                buf = file_ptr.read(read_sz)
            while buf:
                file_hash.update(buf)
                buf = file_ptr.read(read_sz)
            csum = file_hash.hexdigest()

    return csum


def cal_percent(num1: float, num2: float) -> float:
    """
    percentage calculator to track progress
    :param num1: First number
    :param num2: second number
    :return: calculated percentage
    """
    return float(num1) / float(num2) * 100.0


def _format_dict(elist: list) -> dict:
    """
    TODO remove later as IAM is not supported
    Format the data in dict format
    :param elist: list of string element
    """
    resp_dict = dict()
    list_tup = list()
    for i in elist:
        list_tup.append(i.split(" = "))
    for i in list_tup:
        resp_dict[i[0]] = i[1]

    return resp_dict


def format_iam_resp(res_msg: bytes) -> list:
    """
    #TODO remove later as IAM is not supported
    Function to format IAM response which comes in string format.
    :param res_msg: bytes string of tuple
    :return: list of dict
    """
    resp = list()
    res = res_msg.split("b'")[1].replace("\\n',", "").split("\\n")
    for i in res:
        new_result = i.split(',')
        result = _format_dict(new_result)
        resp.append(result)
    return resp


def validate_output(output: str, expected_keywords: str):
    """
    Validate output for expected keywords.
    """
    LOGGER.debug("actual output %s", output)
    output = [i.strip() for i in output]
    LOGGER.debug("output after strip %s", output)
    validation_steps = dict()
    for ele in expected_keywords:
        validation_steps[ele] = False
    for line in output:
        for out in validation_steps:
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            if out in line:
                validation_steps[out] = True
    retval = (False not in list(validation_steps.values()), 'validation failed')
    return retval


def open_empty_file(fpath: str) -> bool:
    """
    Create empty file specified in path
    :param fpath: Non-existing file path.
    :return: True/False
    """
    with open(fpath, "w") as _:
        pass

    return os.path.exists(fpath)


def create_symlink(fpath: str, spath: str) -> bool:
    """
    Create symlink using os.symlink specified in fpath
    :param fpath: Existing file path
    :param spath: Non-existing file path.
    :return: True/err.
    """
    try:
        os.symlink(fpath, spath)
    except OSError as error:
        LOGGER.exception("*ERROR* An exception occurred in %s: %s",
                         create_symlink.__name__, error)
        return False

    return True


def cleanup_dir(dpath: str) -> bool:
    """
    Remove all files, links, directory recursively inside dpath
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
            LOGGER.exception("*ERROR* An exception occurred in %s: %s", cleanup_dir.__name__,
                             error)
            return False

    return True


def list_dir(dpath: str) -> list:
    """
    List directory from dpath
    :param dpath: Directory path.
    """
    try:
        flist = os.listdir(dpath)
        LOGGER.debug("List: %s", str(flist))
    except IOError as error:
        LOGGER.exception("*ERROR* An exception occurred in %s: %s", list_dir.__name__, error)
        return []

    return flist


def make_dir(dpath: str, mode: int = None):
    """
    Create directory path
    :param dpath: Directory path
    :param mode: permission type
    :type dpath: str
    :return: dpath
    :rtype: tuple
    """
    if mode:
        os.mkdir(path=dpath, mode=mode)
    else:
        os.mkdir(dpath)
    return os.path.exists(dpath)


def make_dirs(dpath: str, mode: int = None) -> str:
    """
    Create directory path recursively
    :param dpath: Directory path
    :param mode: permission type
    :return: dpath.
    """
    try:
        if mode:
            os.makedirs(dpath, mode)
        else:
            os.makedirs(dpath)
    except IOError as error:
        LOGGER.exception("*ERROR* An exception occurred in %s: %s", make_dirs.__name__, error)
        return str(error)

    return dpath


def mkdirs(pth):
    """
    Make Directory
    :param pth: Directory path
    """
    try:
        os.makedirs(pth, exist_ok=True)
    except OSError as erroros:
        if erroros.errno != errno.EEXIST:
            raise


def remove_dir(dpath: str) -> bool:
    """
    remove empty directory
    :param dpath: Directory path.
    :return: dpath
    """
    os.rmdir(dpath)

    return os.path.exists(dpath)


def remove_dirs(dpath: str) -> bool:
    """
    Remove directory and hierarchy
    :param dpath: Directory path.
    :return:boolean based on cleanup.
    """
    try:
        shutil.rmtree(dpath)
    except IOError as error:
        LOGGER.exception("*ERROR* An exception occurred in %s: %s", remove_dirs.__name__, error)
        return False

    return True


def get_file_checksum(filename: str):
    """
    This function will return checksum of file content present on the
    local server
    :param  filename: Name of the file
    :return: (Boolean, response)
    """
    LOGGER.debug("Calculating checksum of file content")
    try:
        result = md5(open(filename, "rb").read()).hexdigest()

        return True, result
    except BaseException as error:
        LOGGER.exception("*ERROR* An exception occurred in %s: %s",
                         get_file_checksum.__name__, error)
        return False, error


def get_os_version():
    """Platform independent function to get OS version."""
    if sys.platform == 'win32':
        return platform.system() + platform.release()
    plat, ver, core = platform.dist()
    ver = ver[:3]
    LOGGER.debug("Tests are running on plat %s with ver %s and core %s ", plat, ver, core)
    return plat + ver


def get_host_name():
    """Handle for all OS."""
    return socket.gethostname()


def create_file(fpath: str, count: int, dev: str = "/dev/zero", b_size: str = "1M") -> tuple:
    """
    Create file using dd command
    :param fpath: File path
    :param count: size of the file in MB
    :param dev: Input file used
    :param b_size: block size
    :return:
    """
    proc = None
    try:
        cmd = commands.CREATE_FILE.format(dev, fpath, b_size, count)
        LOGGER.debug(cmd)
        proc = Popen(cmd, shell=True, stderr=PIPE, stdout=PIPE, encoding="utf-8")  # nosec (B603)
        output, error = proc.communicate()
        LOGGER.debug("output = %s", str(output))
        LOGGER.debug("error = %s", str(error))
        if proc.returncode != 0:
            if os.path.isfile(fpath):
                os.remove(fpath)
            raise IOError(f"Unable to create file. command: {cmd}, error: {error}")

        return os.path.exists(fpath), ", ".join([output, error])
    except RuntimeError as ex:
        LOGGER.exception(ex)
        return fpath, ex
    finally:
        if proc:
            proc.terminate()


def create_multiple_size_files(start_range, stop_range, file_count, folder_path, test_filename):
    """
    Creating multiple random size files in a folder
    :param start_range: Start range of the file
    :param stop_range: Stop range of the file
    :param file_count: No of files
    :param folder_path: folder path at which file will be created
    :param test_filename: test file name
    :return: folder list
    """
    if not os.path.exists(folder_path):
        LOGGER.warning("%s doesnt exist creating new one", folder_path)
        os.mkdir(folder_path)
    try:
        os.chdir(folder_path)
        LOGGER.debug("Creating %d file at path %s", file_count, str(os.getcwd()))
        for i in range(file_count):
            filename = "{}{}".format(os.path.join(folder_path, test_filename), i)
            create_file(filename, secrets.SystemRandom().randint(start_range, stop_range))
        dir_list = os.listdir(folder_path)

        return True, dir_list
    except BaseException as error:
        LOGGER.exception("*ERROR* An exception occurred in %s: %s",
                         create_multiple_size_files.__name__, error)
        return False, error


def remove_file(file_path: str = None):
    """
    This function is used to remove file at specified path
    :param file_path: Path of file to be deleted
    :return: (Boolean, Response)
    """
    try:
        os.remove(file_path)

        return True, "Success"
    except BaseException as error:
        LOGGER.exception("*ERROR* An exception occurred in %s: %s", remove_file.__name__, error)
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
        LOGGER.debug("Deleting existing file: %s", str(filename))
        remove_file(filename)
    create_file(filename, size)
    LOGGER.debug("Created new file %s with size %d MB", filename, size)
    dir_path = os.path.dirname(filename)
    secrets.SystemRandom().seed(1048576)
    res_d = list()
    with open(filename, "rb") as fin:
        for ele in range(split_count):
            fop = "{}/{}_out{}".format(dir_path, os.path.basename(filename), str(ele))
            if random_part_size:
                read_bytes = secrets.SystemRandom().randint(1048576 * size // 10, 1048576 * size)
            else:
                read_bytes = (1048576 * size // split_count)
            with open(fop, 'wb') as split_fin:
                split_fin.write(fin.read(read_bytes))
                res_d.append({"Output": fop, "Size": os.stat(fop).st_size})
    LOGGER.debug(res_d)
    return res_d


def is_utility_present(utility_name: str, filepath: str) -> bool:
    """
    This function will check utility file
    is present on specific location or not
    :return: Status(True/False) of command execution
    """
    cmd = f"ls {filepath}"
    try:
        values = run_local_cmd(cmd)
        LOGGER.debug(values)
        if values[0]:
            for val in values[1]:
                if utility_name == val.split("\n")[0]:
                    return True

        return False
    except BaseException as error:
        LOGGER.exception("*ERROR* An exception occurred in %s: %s",
                         is_utility_present.__name__, error)
        return False


def backup_or_restore_files(action, backup_path, backup_list):
    """
    Used to take backup or restore mentioned files at the required path
    """
    rpath = os.getcwd()
    try:
        if action == "backup":
            LOGGER.debug('Starting the backup')
            if not os.path.exists(backup_path):
                os.mkdir(backup_path)
            for files in backup_list:
                shutil.copy(files, backup_path)
                LOGGER.debug("Files :%s copied successfully at path %s", files, backup_path)
            return True, backup_list
        if action == "restore":
            LOGGER.debug('Starting the restore')
            if not os.path.exists(backup_path):
                LOGGER.debug("Backup path :%s, does not exist", str(backup_path))
                return False, "Path not found"
            os.chdir(backup_path)
            for files in backup_list:
                file = os.path.basename(files)
                file_path = os.path.dirname(files)
                shutil.copy(file, file_path)
                LOGGER.debug("File :%s got copied successfully at path %s", file, file_path)
            os.chdir(rpath)
            return True, backup_path
        return False, "NO action mentioned"
    except BaseException as error:
        LOGGER.exception("*ERROR* An exception occurred in %s: %s",
                         backup_or_restore_files.__name__, error)
        os.chdir(rpath)
        return False, error


def is_dir_exists(path: str, dir_name: str) -> bool:
    """
    Check directory path exists.
    """
    status, directories = run_local_cmd(commands.LS_CMD.format(path))
    directories = (directory.split("\n")[0] for directory in directories)
    if dir_name in directories and status:
        return True

    return False


def is_machine_clean() -> Tuple[bool, bool]:
    """
    This function checks that any rpm is installed on machine and
    will check for eos-prvsnr binaries present at /opt/seagate/ path
    ex -
    rpm_cmd = "rpm -qa | grep eos-prvsnr"
    bin_cmd = "ls /opt/seagate/"
    :return: boolean values for both scenarios
    """
    rpm_installed = False
    eos_prvsnr_present = False

    # Check any RPM is being installed on machine
    rpm_cmd = commands.LST_RPM_CMD
    prvsn_dir = commands.LST_PRVSN_DIR
    LOGGER.debug("command : %s", rpm_cmd)
    cmd_output = run_local_cmd(rpm_cmd)
    if cmd_output[1]:
        rpm_installed = True

    # Now check eos-prvsn binaries present at path
    LOGGER.debug("command : %s", prvsn_dir)
    cmd_output_1 = run_local_cmd(prvsn_dir)
    if cmd_output_1[1]:
        eos_prvsnr_present = True

    return rpm_installed, eos_prvsnr_present


def is_rpm_installed(expected_rpm: str, remote: bool = False, **remotekwargs) -> tuple:
    """
    This function checks that expected rpm is currently installed or not
    :param remote: If True command executed on remote machine
    :param expected_rpm: rpm to check
    :param remotekwargs: host details if remote execute is true
    :return: True if rpm is installed, false otherwise.
    """
    if not expected_rpm:
        return False, "Please, provide valid expected rpm: {}".format(expected_rpm)

    cmd = commands.RPM_GREP_CMD.format(expected_rpm)
    LOGGER.debug("command: %s", cmd)
    cmd_output = execute_cmd(cmd=cmd, remote=remote, **remotekwargs)
    LOGGER.debug(cmd_output)
    if not (cmd_output[0] or expected_rpm in cmd_output[1]):
        return False, cmd_output[1]

    return True, cmd_output[1]


def install_new_cli_rpm(*remoteargs, rpm_link=None, remote=False, **remotekwargs):
    """
    Install rmps.
    """
    cmd = commands.RPM_INSTALL_CMD.format(rpm_link)
    LOGGER.debug("command : %s", cmd)
    cmd_output = execute_cmd(cmd, remote, *remoteargs, **remotekwargs)
    if cmd_output:
        LOGGER.debug("Successfully installed RPM")

    return cmd_output


def list_rpms(*remoteargs, filter_str="", remote=False,
              **remotekwargs) -> Tuple[bool, list]:
    """
    This function lists the rpms installed on a given host and filters by given string
    :param str filter_str: string to search in rpm names for filtering results,
    default lists all the rpms
    :param remote: if True executes on remote machine
    :return: True/False, list of rpms
    """
    cmd = commands.RPM_GREP_CMD.format(filter_str)
    LOGGER.debug("command : %s", cmd)
    resp = execute_cmd(cmd, remote, *remoteargs, **remotekwargs)
    if isinstance(resp, list):
        rpm_list = [rpm.strip("\n") for rpm in resp]
        if not rpm_list:
            return False, rpm_list
        return True, rpm_list

    return False, resp


def check_ping(host: str) -> bool:
    """
    This function will send ping to the given host
    :param str host: Host to whom ping to be sent
    :return: True/ False
    """
    response = os.system("ping -c 1 {}".format(host))

    return response == 0


def pgrep(process: str):
    """
    Function to get process ID using pgrep cmd
    :param process: Name of the process
    :return: response
    """
    response = run_local_cmd(commands.PGREP_CMD.format(process))
    return response


def get_disk_usage(path: str) -> str:
    """
    This function will return disk usage associated with given path
    :param path: Path to retrieve disk usage
    :return: Disk usage of given path
    """
    LOGGER.debug("Running local disk usage cmd.")
    stats = os.statvfs(path)
    f_blocks, f_frsize, f_bfree = stats.f_blocks, stats.f_frsize, stats.f_bfree
    total = (f_blocks * f_frsize)
    used = (f_blocks - f_bfree) * f_frsize
    result = format((float(used) / total) * 100, ".1f")

    return result


def path_exists(path: str) -> bool:
    """
    This function will return true if path exists else false
    :param path: file/directory path.
    :return: bool
    """
    status = os.path.exists(path)

    return status


def file_lock(lock_file, non_blocking=False):
    """
    Uses the :func:`msvcrt.locking` function to hard lock the lock file on
    Windows systems.
    """

    if sys.platform == 'win32':
        open_mode = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        lock_file_fd = None
        try:
            lock_file_fd = os.open(lock_file, open_mode)
        except OSError:
            pass
        else:
            try:
                msvcrt.locking(lock_file_fd, msvcrt.LK_LOCK, 1)
            except (IOError, OSError):
                os.close(lock_file_fd)
                return None, False
            else:
                LOGGER.debug("Lock file created.")
        return lock_file_fd, True
    if not lock_file.startswith('/'):
        # If Not an absolute path name, prefix in $HOME/.runner
        fname = os.path.join(os.getenv('HOME'), '.runner', lock_file)

    fdir = os.path.dirname(fname)
    if not os.path.exists(fdir):
        os.makedirs(fdir)

    try:
        fmutex = open(fname, "rb+")
    except (OSError, IOError):
        fmutex = open(fname, "wb+")
    try:
        flags = fcntl.LOCK_EX
        if non_blocking:
            flags |= fcntl.LOCK_NB
        fcntl.flock(fmutex.fileno(), flags)
    except IOError:
        return None, False

    return fmutex, True


def file_unlock(fmutex, path=''):
    """
    Unlock the file lock
    :param path: Lock file path
    :param fmutex: File lock
    :return:
    """
    if sys.platform == 'win32':
        msvcrt.locking(fmutex, msvcrt.LK_UNLCK, 1)
        os.close(fmutex)
        remove_lck_file(path)
    else:
        fcntl.flock(fmutex.fileno(), fcntl.LOCK_UN)
        fmutex.close()
        remove_lck_file(path)


def remove_lck_file(path):
    """Remove lock file."""
    try:
        os.remove(path)
    # Probably another instance of the application
    # that acquired the file lock.
    except FileNotFoundError:
        pass
    except OSError:
        pass


def insert_into_builtins(name, obj):
    """May be required in worst case."""
    if isinstance(builtins, dict):
        builtins[name] = obj
    else:
        builtins.obj = obj


def mount_upload_to_server(host_dir: str = None, mnt_dir: str = None,
                           remote_path: str = None, local_path: str = None) \
        -> tuple:
    """Mount NFS directory and upload file to NFS
    :param host_dir: Link of NFS server directory
    :param mnt_dir: Path of directory to be mounted
    :param remote_path: Dir Path to which file is to be uploaded on NFS server
    :param local_path: Local path of the file to be uploaded
    :return: Bool, response"""
    try:
        if not os.path.ismount(mnt_dir):
            if not os.path.exists(mnt_dir):
                LOGGER.info("Creating a mount directory to share")
                make_dirs(dpath=mnt_dir)

            cmd = commands.CMD_MOUNT.format(host_dir, mnt_dir)
            resp = run_local_cmd(cmd=cmd)
            if not resp[0]:
                return resp

        new_path = os.path.join(mnt_dir, remote_path)
        LOGGER.info("Creating directory on server")
        if not os.path.exists(new_path):
            make_dirs(dpath=new_path)

        LOGGER.info("Copying file to mounted directory")
        LOGGER.info("local path and new path are %s\n%s", local_path, new_path)
        if os.path.isfile(local_path):
            LOGGER.debug("Copy from %s to %s", local_path, new_path)
            shutil.copy(local_path, new_path)
        else:
            LOGGER.debug("Copy in else")
            shutil.copytree(local_path, os.path.join(new_path, os.path.basename(local_path)))
        log_path = os.path.join(host_dir, remote_path)

    except BaseException as error:
        LOGGER.exception(error)
        LOGGER.info("Copying file to local path")
        log_path = os.path.join(params.LOCAL_LOG_PATH, remote_path)
        if not os.path.exists(log_path):
            LOGGER.info("Creating local log directory")
            make_dirs(dpath=log_path)

        if os.path.isfile(local_path):
            shutil.copy(local_path, log_path)
        else:
            shutil.copytree(local_path, os.path.join(log_path, os.path.basename(local_path)))

    return True, log_path


def umount_dir(mnt_dir: str = None) -> tuple:
    """Function to unmount directory
    :param mnt_dir: Path of mounted directory
    :return: Bool, response"""
    if os.path.ismount(mnt_dir):
        LOGGER.info("Unmounting mounted directory")
        cmd = commands.CMD_UMOUNT.format(mnt_dir)
        resp = run_local_cmd(cmd=cmd)
        if not resp[0]:
            return resp

        while True:
            if not os.path.ismount(mnt_dir):
                break

        remove_dir(dpath=mnt_dir)

    return True, "Directory is unmounted"


def get_s3_url(cfg, node_index):
    """
    Function to format s3 url for individual vm
    :param cfg: config object
    :param node_index: node index for indexing s3_dns fqdn
    :return: dict respo with s3_url and iam_url as key
    """
    final_urls = dict()
    final_urls["s3_url"] = f"https://{cfg['s3_dns'][node_index]}"
    final_urls["iam_url"] = f"https://{cfg['s3_dns'][node_index]}:9443"
    return final_urls


def random_string_generator(
        size: int = 6,
        chars: str = string.ascii_uppercase + string.digits + string.ascii_lowercase) -> str:
    """
    Generate random string of given size
    :param size: Length of string
    :param chars: Characters from which random selection is done
    :return: str
    """
    return ''.join(secrets.SystemRandom().choice(chars) for _ in range(size))


def create_file_fallocate(filepath=None, size="1MB", option="l"):
    """
    Create file using tool fallocate
    :param filepath: Absolute/Relative filepath
    :param size: file size: 1k, 33k, 1MB, 4MB etc.
    :param option: options supported by fallocate tool
    :return: True/False, response.
    """
    command = "fallocate -{} {} {}".format(option, size, filepath)
    resp = run_local_cmd(command)

    return os.path.exists(filepath), resp[1]


def toggle_nw_status(device: str, status: str, host: str, username: str, pwd: str):
    """
    Toggle network device status using ip set command
    :param str device: Name of the ip network device
    :param str status: Expect status like up/down
    :param host: Host name on which command is to be run
    :param username: Username of host
    :param pwd: Password of host
    :return: True/False
    :rtype: Boolean
    """
    LOGGER.info("Changing %s n/w device status to %s", device, status)
    cmd = commands.IP_LINK_CMD.format(device, status)
    LOGGER.info("Running command: %s", cmd)
    res = run_remote_cmd(hostname=host, username=username, password=pwd, cmd=cmd, read_lines=True)
    LOGGER.debug("Response: %s", res)

    LOGGER.debug(res)
    return res[0]


def create_dir_hierarchy_and_objects(directory_path=None,
                                     obj_prefix=None,
                                     depth: int = 1,
                                     obj_count: int = 1,
                                     **kwargs) -> list:
    """
    Create directory hierarchy as per depth and create number of objects in each folder
    :param directory_path: Absolute path of root directory
    :param obj_prefix: Name of the object prefix
    :param depth: Directory hierarchy
    :param obj_count: object count per directory
    :keyword b_size: object block size
    :keyword count: count
    :return: file path list.
    """
    file_path_list = list()
    count = kwargs.get("count", 1)
    b_size = kwargs.get("b_size", 1)
    for objcnt in range(obj_count):
        fpath = os.path.join(directory_path,
                             f"{obj_prefix}{objcnt}{time.perf_counter_ns()}.txt")
        run_local_cmd(
            commands.CREATE_FILE.format("/dev/zero", fpath, count, b_size))
        if os.path.exists(fpath):
            file_path_list.append(fpath)
    for dcnt in range(depth):
        directory_path = os.path.join(
            directory_path, ''.join(
                secrets.SystemRandom().choice(
                    string.ascii_lowercase) for _ in range(
                    5 + dcnt)))
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        for objcnt in range(obj_count):
            fpath = os.path.join(
                directory_path,
                f"{obj_prefix}{objcnt}{time.perf_counter_ns()}.txt")
            run_local_cmd(
                commands.CREATE_FILE.format("/dev/zero", fpath, count, b_size))
            if os.path.exists(fpath):
                file_path_list.append(fpath)
    LOGGER.info("File list: %s", file_path_list)

    return file_path_list


def validate_s3bench_parallel_execution(log_dir=None, log_prefix=None, log_path=None) -> tuple:
    """
    Validate the s3bench parallel execution log file for failure
    :param log_dir: Log directory path
    :param log_prefix: s3 bench log prefix
    :param log_path: s3 bench log path
    :return: bool, response.
    """
    LOGGER.info("S3 parallel ios log validation started...")
    if log_dir and os.path.isdir(log_dir):
        log_path = [filepath for filepath in sorted(
            glob.glob(os.path.abspath(log_dir) + '/**'),
            key=os.path.getctime)
                    if os.path.basename(filepath).startswith(log_prefix)][-1]
    LOGGER.info("IO log path: %s", log_path)
    if not os.path.isfile(log_path):
        return False, f"failed to generate logs for parallel run: {log_prefix}."
    lines = open(log_path).readlines()
    resp_filtered = [
        line for line in lines if 'Errors Count:' in line and "reportFormat" not in line]
    LOGGER.info("'Error count' filtered list: %s", resp_filtered)
    for response in resp_filtered:
        if int(response.split(":")[1].strip()) != 0:
            return False, response
    LOGGER.info("Observed no Error count in io log.")
    error_kws = ["with error ", "panic", "status code", "exit status 2",
                 "InternalError", "ServiceUnavailable"]
    for error in error_kws:
        if error in ",".join(lines):
            return False, f"{error} Found in S3Bench Run."
    LOGGER.info("Observed no Error keyword '%s' in io log.", error_kws)
    # remove_file(log_path)  # Keeping logs for FA/Debugging.
    LOGGER.info("S3 parallel ios log validation completed...")

    return True, "S3 parallel ios completed successfully."


def toggle_nw_infc_status(device: str, status: str, host: str, username: str,
                          pwd: str):
    """
    Toggle network interface status using ip set command
    :param str device: Name of the ip network device
    :param str status: Expect status like up/down
    :param host: Host name on which command is to be run
    :param username: Username of host
    :param pwd: Password of host
    :return: True/False
    :rtype: Boolean
    """
    LOGGER.info("Changing %s n/w device status to %s", device, status)
    cmd = commands.IF_CMD.format(status, device)
    LOGGER.info("Running command: %s", cmd)
    res = run_remote_cmd(hostname=host, username=username, password=pwd, cmd=cmd, read_lines=True)
    LOGGER.debug("Response: %s", res)

    LOGGER.debug(res)
    return res[0]


def validate_checksum(file_path_1: str, file_path_2: str, **kwargs):
    """
    validate MD5 checksum for 2 files
    # :param hash_algo: calculate checksum for given hash algo
    """
    hash_algo = kwargs.get("hash_algo", "md5")
    check_1 = calculate_checksum(file_path=file_path_1, hash_algo=hash_algo)
    check_2 = calculate_checksum(file_path=file_path_2, hash_algo=hash_algo)
    if check_1 == check_2:
        return True
    return False
