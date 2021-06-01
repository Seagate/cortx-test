#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Module to maintain system utils."""

import logging
import os
import sys
import time
import platform
import random
import shutil
import socket
import builtins
import errno
import string
from typing import Tuple
from subprocess import Popen, PIPE
from hashlib import md5
from paramiko import SSHClient, AutoAddPolicy
from commons import commands
from commons import params

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


def run_remote_cmd(
        cmd: str,
        hostname: str,
        username: str,
        password: str,
        **kwargs) -> tuple:
    """
    Execute command on remote machine.
    :return: stdout
    """
    LOGGER.info(
        "Host: %s, User: %s, Password: %s",
        hostname,
        username,
        password)
    read_lines = kwargs.get("read_lines", False)
    read_nbytes = kwargs.get("read_nbytes", -1)
    timeout_sec = kwargs.get("timeout_sec", 30)
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    LOGGER.debug("Command: %s", str(cmd))
    client.connect(hostname, username=username,
                   password=password, timeout=timeout_sec)
    _, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    if read_lines:
        output = stdout.readlines()
        output = [r.strip().strip("\n").strip() for r in output]
        LOGGER.debug("Result: %s", str(output))
        error = stderr.readlines()
        error = [r.strip().strip("\n").strip() for r in error]
        LOGGER.debug("Error: %s", str(error))
    else:
        output = stdout.read(read_nbytes)
        LOGGER.debug("Result: %s", str(output))
        error = stderr.read()
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


def run_local_cmd(cmd: str = None, flg: bool = False) -> tuple:
    """
    Execute any given command on local machine(Windows, Linux).
    :param cmd: command to be executed.
    :param flg: To get str(proc.communicate())
    :return: bool, response.
    """
    if not cmd:
        raise ValueError("Missing required parameter: {}".format(cmd))
    LOGGER.debug("Command: %s", cmd)
    proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, error = proc.communicate()
    LOGGER.debug("output = %s", str(output))
    LOGGER.debug("error = %s", str(error))
    if flg:
        return True, str((output, error))
    if proc.returncode != 0:
        return False, str(error)
    if b"Number of key(s) added: 1" in output:
        return True, str(output)
    if b"command not found" in error or \
            b"not recognized as an internal or external command" in error or error:
        return False, str(error)

    return True, str(output)


def execute_cmd(cmd: str, remote: bool = False, *remoteargs, **remoteKwargs) -> tuple:
    """Execute command on local / remote machine based on remote flag
    :param cmd: cmd to be executed
    :param remote: if True executes on remote machine
    """
    if remote:
        result = run_remote_cmd(cmd, *remoteargs, **remoteKwargs)
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


def calculate_checksum(
        file_path: str,
        binary_bz64: bool = True,
        options: str = "") -> tuple:
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

    LOGGER.debug("Executing cmd: %s", cmd)
    result = run_local_cmd(cmd)
    LOGGER.debug("Output: %s", str(result))
    return result


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
    resp = []
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
    retval = (
        False not in list(
            validation_steps.values()),
        'validation failed')
    return retval


def open_empty_file(fpath: str) -> bool:
    """
    Create empty file specified in path.
    :param fpath: Non-existing file path.
    :return: True/False
    """
    with open(fpath, "w") as _:
        pass

    return os.path.exists(fpath)


def create_symlink(fpath: str, spath: str) -> bool:
    """
    Create symlink using os.symlink specified in fpath.
    :param fpath: Existing file path.
    :param spath: Non-existing file path.
    :return: True/err.
    """
    try:
        os.symlink(fpath, spath)
    except OSError as error:
        LOGGER.error(
            "*ERROR* An exception occurred in %s: %s",
            create_symlink.__name__,
            error)
        return False

    return True


def cleanup_dir(dpath: str) -> bool:
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
            LOGGER.error(
                "*ERROR* An exception occurred in %s: %s",
                cleanup_dir.__name__,
                error)
            return False

    return True


def list_dir(dpath: str) -> list:
    """
    List directory from dpath.
    :param dpath: Directory path.
    """
    try:
        flist = os.listdir(dpath)
        LOGGER.debug("List: %s", str(flist))
    except IOError as error:
        LOGGER.error(
            "*ERROR* An exception occurred in %s: %s",
            list_dir.__name__,
            error)
        return []

    return flist


def make_dir(dpath: str, mode: int = None):
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


def make_dirs(dpath: str, mode: int = None) -> str:
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
        LOGGER.error(
            "*ERROR* An exception occurred in %s: %s",
            make_dirs.__name__,
            error)
        return str(error)

    return dpath


def mkdirs(pth):
    try:
        os.makedirs(pth, exist_ok=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def remove_dir(dpath: str) -> bool:
    """
    remove empty directory.
    :param dpath: Directory path.
    :return: dpath
    """
    os.rmdir(dpath)

    return os.path.exists(dpath)


def remove_dirs(dpath: str) -> bool:
    """
    Remove directory and hierarchy.
    :param dpath: Directory path.
    :return:boolean based on cleanup.
    """
    try:
        shutil.rmtree(dpath)
    except IOError as error:
        LOGGER.error(
            "*ERROR* An exception occurred in %s: %s",
            remove_dirs.__name__,
            error)
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
        LOGGER.error("*ERROR* An exception occurred in %s: %s",
                     get_file_checksum.__name__, error)
        return False, error


def get_os_version():
    """Platform independent function to get OS version."""
    if sys.platform == 'win32':
        return platform.system() + platform.release()
    else:
        plat, ver, core = platform.dist()
        ver = ver[:3]
        LOGGER.debug("Tests are running on plat %s with ver %s and core %s ", plat, ver, core)
        return plat + ver


def get_host_name():
    """Handle for all OS."""
    return socket.gethostname()


def create_file(
        fpath: str,
        count: int,
        dev: str = "/dev/zero",
        b_size: str = "1M") -> tuple:
    """
    Create file using dd command.
    :param fpath: File path.
    :param count: size of the file in MB.
    :param dev: Input file used.
    :param b_size: block size.
    :return:
    """
    cmd = commands.CREATE_FILE.format(dev, fpath, b_size, count)
    LOGGER.debug(cmd)
    proc = Popen(cmd, shell=True, stderr=PIPE, stdout=PIPE, encoding="utf-8")
    output, error = proc.communicate()
    LOGGER.debug("output = %s", str(output))
    LOGGER.debug("error = %s", str(error))
    if proc.returncode != 0:
        if os.path.isfile(fpath):
            os.remove(fpath)
        raise IOError(f"Unable to create file. command: {cmd}, error: {error}")

    return os.path.exists(fpath), ", ".join([output, error])


def create_multiple_size_files(
        start_range,
        stop_range,
        file_count,
        folder_path,
        test_filename):
    """
    Creating multiple random size files in a folder
    :param start_range: Start range of the file
    :param stop_range: Stop range of the file
    :param file_count: No of files
    :param folder_path: folder path at which file will be created
    :return: folder list
    """
    if not os.path.exists(folder_path):
        LOGGER.warning("%s doesnt exist creating new one", folder_path)
        os.mkdir(folder_path)
    try:
        os.chdir(folder_path)
        LOGGER.debug("Creating %d file at path %s",
                     file_count, str(os.getcwd()))
        for i in range(file_count):
            filename = "{}{}".format(
                os.path.join(folder_path, test_filename), i)
            create_file(filename, random.randint(start_range, stop_range))
        dir_list = os.listdir(folder_path)

        return True, dir_list
    except BaseException as error:
        LOGGER.error("*ERROR* An exception occurred in %s: %s",
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
    except Exception as error:
        LOGGER.error(
            "*ERROR* An exception occurred in %s: %s",
            remove_file.__name__,
            error)
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
    LOGGER.debug(
        "Created new file %s with size %d MB",
        filename, size)
    dir_path = os.path.dirname(filename)
    random.seed(1048576)
    res_d = list()
    with open(filename, "rb") as fin:
        for ele in range(split_count):
            fop = "{}/{}_out{}".format(dir_path,
                                       os.path.basename(filename), str(ele))
            if random_part_size:
                read_bytes = random.randint(
                    1048576 * size // 10, 1048576 * size)
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
        LOGGER.error("*ERROR* An exception occurred in %s: %s",
                     is_utility_present.__name__, error)
        return False


def backup_or_restore_files(action,
                            backup_path,
                            backup_list):
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
                LOGGER.debug(
                    "Files :%s copied successfully at path %s",
                    files, backup_path)
            return True, backup_list
        if action == "restore":
            LOGGER.debug('Starting the restore')
            if not os.path.exists(backup_path):
                LOGGER.debug(
                    "Backup path :%s, does not exist", str(backup_path))
            else:
                os.chdir(backup_path)
                for files in backup_list:
                    file = os.path.basename(files)
                    file_path = os.path.dirname(files)
                    shutil.copy(file, file_path)
                    LOGGER.debug(
                        "File :%s got copied successfully at path %s",
                        file, file_path)
                os.chdir(rpath)
                return True, backup_path
    except BaseException as error:
        LOGGER.error("*ERROR* An exception occurred in %s: %s",
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
    :return: boolean values for both scenarioes
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


def is_rpm_installed(
        expected_rpm: str,
        remote: bool = False,
        **remoteKwargs) -> tuple:
    """
    This function checks that expected rpm is currently installed or not.

    :param remote: If True command executed on remote machine.
    :param expected_rpm: rpm to check.
    :param remoteKwargs: host details if remote execute is true.
    :return: True if rpm is installed, false otherwise.
    """
    if not expected_rpm:
        return False, "Please, provide valid expected rpm: {}".format(expected_rpm)

    cmd = commands.RPM_GREP_CMD.format(expected_rpm)
    LOGGER.debug("command: %s", cmd)
    cmd_output = execute_cmd(cmd=cmd, remote=remote, **remoteKwargs)
    LOGGER.debug(cmd_output)
    if not (cmd_output[0] or expected_rpm in cmd_output[1]):
        return False, cmd_output[1]

    return True, cmd_output[1]


def install_new_cli_rpm(
        *remoteargs,
        rpm_link=None,
        remote=False,
        **remoteKwargs):
    """
    Install rmps.
    """
    cmd_output = list()
    # cmd = f"yum install -y {rpm_link}"
    cmd = commands.RPM_INSTALL_CMD.format(rpm_link)
    LOGGER.debug("command : %s", cmd)
    cmd_output = execute_cmd(cmd, remote, *remoteargs, **remoteKwargs)
    if cmd_output:
        LOGGER.debug("Successfully installed RPM")

    return cmd_output


def list_rpms(*remoteargs, filter_str="", remote=False,
              **remoteKwargs) -> Tuple[bool, list]:
    """
    This function lists the rpms installed on a given host and filters by given string.
    :param str filter_str: string to search in rpm names for filtering results,
    default lists all the rpms.
    :return: True/False, list of rpms
    """
    cmd = commands.RPM_GREP_CMD.format(filter_str)
    LOGGER.debug("command : %s", cmd)
    resp = execute_cmd(cmd, remote, *remoteargs, **remoteKwargs)
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
    Function to get process ID using pgrep cmd.
    :param process: Name of the process
    :return: response
    """
    response = run_local_cmd(commands.PGREP_CMD.format(process))
    return response


def get_disk_usage(path: str) -> str:
    """
    This function will return disk usage associated with given path.
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
    This function will return true if path exists else false.

    :param path: file/directory path.
    :return: bool
    """
    status = os.path.exists(path)

    return status


def file_lock(lock_file, non_blocking=False):
    """
    Uses the :func:`msvcrt.locking` function to hard lock the lock file on
    windows systems.
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

    else:
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
    Unlock the file lock.
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
                resp = make_dirs(dpath=mnt_dir)

            cmd = commands.CMD_MOUNT.format(host_dir, mnt_dir)
            resp = run_local_cmd(cmd=cmd)
            if not resp[0]:
                return resp

        new_path = os.path.join(mnt_dir, remote_path)
        LOGGER.info("Creating directory on server")
        if not os.path.exists(new_path):
            resp = make_dirs(dpath=new_path)

        LOGGER.info("Copying file to mounted directory")
        shutil.copy(local_path, new_path)
        log_path = os.path.join(host_dir.split(":")[0], remote_path)
    except Exception as error:
        LOGGER.error(error)
        LOGGER.info("Copying file to local path")
        log_path = os.path.join(params.LOCAL_LOG_PATH, remote_path)
        if not os.path.exists(log_path):
            LOGGER.info("Creating local log directory")
            resp = make_dirs(dpath=log_path)

        shutil.copy(local_path, log_path)

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


def configure_jclient_cloud(
        source: str,
        destination: str,
        nfs_path: str,
        ca_crt_path: str) -> bool:
    """
        Function to configure jclient and cloud jar files
        :param ca_crt_path: s3 ca.crt path.
        :param nfs_path: nfs server path where jcloudclient.jar, jclient.jar present.
        :param source: path to the source dir where .jar are present.
        :param destination: destination path where .jar need to be copied
        """
    if not os.path.exists(source):
        os.mkdir(source)

    dir_list = os.listdir(source)
    if "jcloudclient.jar" not in dir_list or "jclient.jar" not in dir_list:
        temp_dir = "/mnt/jjarfiles"
        os.mkdir(temp_dir)
        mount_cmd = f"mount.nfs -v {nfs_path} {temp_dir}"
        umount_cmd = f"umount -v {temp_dir}"
        run_local_cmd(mount_cmd)
        run_local_cmd(f"yes | cp -rf {temp_dir}*.jar {source}")
        run_local_cmd(umount_cmd)
        os.remove(temp_dir)

    run_local_cmd(f"yes | cp -rf {source}*.jar {destination}")
    res_ls = run_local_cmd(f"ls {destination}")[1]
    # Run commands to set cert files in client Location.
    run_local_cmd(commands.CMD_KEYTOOL1)
    run_local_cmd(commands.CMD_KEYTOOL2.format(ca_crt_path))

    return bool(".jar" in res_ls)


def configre_minio_cloud(minio_repo=None,
                         endpoint_url=None,
                         s3_cert_path=None,
                         minio_cert_path_list=None,
                         **kwargs):
    """
    Installing minio client in current machine.

    :param minio_repo: minio repo path.
    :param endpoint_url: s3 endpoint url.
    :param s3_cert_path: s3 certificate path.
    :param minio_cert_path_list: minio path list to be updated.
    :param kwargs: access, secret keys.
    :return: True if setup completed or false.
    """
    try:
        LOGGER.info("Installing minio client in current machine.")
        ACCESS = kwargs.get("access", None)
        SECRET = kwargs.get("secret", None)
        run_local_cmd("wget {}".format(minio_repo))
        run_local_cmd("chmod +x {}".format(os.path.basename(minio_repo)))
        run_local_cmd("./{} config host add s3 {} {} {} --api S3v4".format(os.path.basename(
            minio_repo), endpoint_url, ACCESS, SECRET))
        for crt_path in minio_cert_path_list:
            if not os.path.exists(crt_path):
                run_local_cmd("yes | cp -r {} {}".format(s3_cert_path, crt_path))
        LOGGER.info("Installed minio client in current machine.")

        return True
    except Exception as error:
        LOGGER.error(str(error))
        return False


def random_metadata_generator(
        size: int = 6,
        chars: str = string.ascii_uppercase + string.digits + string.ascii_lowercase) -> str:
    """
    Generate random string of given size

    :param size: Length of string
    :param chars: Characters from which random selection is done
    :return: str
    """
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


def create_file_fallocate(filepath=None, size="1MB", option="l"):
    """
    Create file using tool fallocate.

    :param filepath: Absolute/Relative filepath.
    :param size: file size: 1k, 33k, 1MB, 4MB etc.
    :param option: options supported by fallocate tool.
    :return: True/False, response.
    """
    command = "fallocate -{} {} {}".format(option, size, filepath)
    resp = run_local_cmd(command)

    return os.path.exists(filepath), resp[1]


def toggle_nw_status(device: str, status: str, host: str, username: str,
                     pwd: str):
    """
    Toggle network device status using ip set command.
    :param str device: Name of the ip network device
    :param str status: Expect status like up/down
    :param host: Host name on which command is to be run
    :param username: Username of host
    :param pwd: Password of host
    :return: True/False
    :rtype: Boolean
    """
    LOGGER.info(f"Changing {device} n/w device status to {status}")
    cmd = commands.IP_LINK_CMD.format(device, status)
    res = run_remote_cmd(
            hostname=host, username=username, password=pwd, cmd=cmd,
            read_lines=True)
    LOGGER.debug(f"Command: {cmd}, response: {res}")

    LOGGER.debug(res)
    return res[0]


def create_dir_hierarchy_and_objects(directory_path=None,
                                     obj_prefix=None,
                                     depth: int = 1,
                                     obj_count: int = 1,
                                     **kwargs) -> list:
    """
    Create directory hierarchy as per depth and create number of objects in each folder.

    :param directory_path: Absolute path of root directory.
    :param obj_prefix: Name of the object prefix.
    :param depth: Directory hierarchy.
    :param obj_count: object count per directory.
    :param b_size: object block size.
    :param count: count.
    :return: file path list.
    """
    file_path_list = []
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
                random.SystemRandom().choice(
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
