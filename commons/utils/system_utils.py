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

################################################################################
# Local libraries
################################################################################


################################################################################
# Constants
################################################################################
log = logging.getLogger(__name__)

################################################################################
# RPM functions
################################################################################

def list_rpms(host, user, passwd, filter_str=""):
    """
    This function lists the rpms installed on a given host and filters by given string
    :param str filter_str: string to search in rpm names for filtering results, default lists all the rpms
    :param str host: hostname or IP of the host
    :param str user: username of host
    :param str passwd: password of host
    :return: True/False, list of rpms
    :rtype: boolean, list
    """
    rpm_grep_cmd = "rpm -qa | grep {}".format(filter_str)
    resp = self.remote_execution(
        host=host,
        user=user,
        password=passwd,
        cmd=rpm_grep_cmd)
    if isinstance(resp, list):
        rpm_list = [rpm.strip("\n") for rpm in resp]
        if not rpm_list:
            return False, rpm_list
        return True, rpm_list
    else:
        return False, resp

def install_new_cli_rpm(host=None, rpm_link=None):
    cmd_output = []
    try:
        # cmd = f"yum install -y {rpm_link}"
        cmd = constants.RPM_INSTALL_CMD.format(rpm_link)
        log.info(f"command : {cmd}")
        cmd_flag, cmd_output = self.execute_command(command=cmd, host=host)
        if cmd_flag and cmd_output != []:
            log.info(constants.RPM_INSTALLATION_SUCCESS)
        return cmd_flag, cmd_output
    except Exception as error:
        log.error("{0} {1}: {2}".format(
            constants.RPM_INSTALLATION_FAILED,
            self.install_new_cli_rpm.__name__,
            error))
        return False, cmd_output

def is_rpm_installed(self, expected_rpm, host=None):
    """
    This function checks that expected rpm is currenty installed or not
    :param expected_rpm: rpm to check
    :type expected_rpm: string
    :return: True if rpm is installed, false otherwise
    :param host: Remote machine IP to connect
    :type host: str
    """
    rpm_installed = False
    cmd = PROV_DICT_OBJ["LST_RPM_CMD"]
    log.info(f"command : {cmd}")
    cmd_output = self.execute_command(command=cmd, host=host)
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

def is_machine_clean(self):
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
    rpm_cmd = PROV_DICT_OBJ["LST_RPM_CMD"]
    prvsn_dir = constants.LST_PRVSN_DIR
    log.info(f"command : {rpm_cmd}")
    cmd_output = self.execute_command(command=rpm_cmd)
    if cmd_output[1] != []:
        rpm_installed = True

    # Now check eos-prvsn binaries present at path
    log.info(f"command : {prvsn_dir}")
    cmd_output_1 = self.execute_command(command=prvsn_dir)
    if cmd_output_1[1] != []:
        eos_prvsnr_present = True
    return rpm_installed, eos_prvsnr_present

################################################################################
# Math operations
################################################################################

    def calculate_checksum(self, file_path, binary_bz64=True, options=""):
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
        result = self.execute_cmd(cmd)
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
        log.info("actual output", output)
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
    def open_empty_file(self,
                        fpath,
                        ):
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
            log.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.open_empty_file.__name__,
                error))
            return False
        return True

    def create_symlink(self,
                       fpath,
                       spath,
                       ):
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
            log.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.create_symlink.__name__,
                error))
            return False

        return True

    def cleanup_directory(self,
                          dpath,
                          ):
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
                log.error("{0} {1}: {2}".format(
                    constants.EXCEPTION_ERROR,
                    Utility.cleanup_directory.__name__,
                    error))
                return False

        return True

    def listdir(self,
                dpath,
                ):
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
            log.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.listdir.__name__,
                error))
            return []

        return flist

    def makedir(self,
                dpath,
                mode=None,
                ):
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
            log.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.update_config.__name__,
                error))
            return str(error)

        return dpath

    def makedirs(self,
                 dpath,
                 mode=None,
                 ):
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
            log.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.makedirs.__name__,
                error))
            return str(error)

        return dpath

    def removedir(self,
                  dpath,
                  ):
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
            log.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.removedir.__name__,
                error))
            return str(error)

        return dpath

    def get_file_checksum(self, file_name):
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
            log.error(
                "{0} {1}: {2}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_file_checksum.__name__,
                    error))
            return False, error

    def create_multiple_size_files(
            self,
            start_range,
            stop_range,
            file_count,
            folder_path=CM_CFG["test_folder_path"]):
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
                file_name = "{}{}".format(
                    os.path.join(
                        folder_path,
                        CM_CFG["test_file_name"]),
                    i)
                self.create_file(
                    file_name, random.randint(
                        start_range, stop_range))
            list_dir = os.listdir(folder_path)
            return True, list_dir
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.create_multiple_size_files.__name__,
                    error))
            return False, error

    def remove_file(self, file_path=None):
        """
        This function is used to remove file at specified path
        :param file_path: Path of file to be deleted
        :return: (Boolean, Response)
        """
        try:
            os.remove(file_path)
            return True, "Success"
        except Exception as error:
            log.error("Error while deleting file".format(error))
            return False, error
    def split_file(self, file_name, size, split_count, random_part_size=False):
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
            self.remove_file(file_name)
        self.create_file(file_name, size)
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
            values = self.execute_command(cmd)
            log.info(values)
            if values[0]:
                for val in values[1]:
                    if utility_name == val.split("\n")[0]:
                        return True
            return False
        except BaseException as error:
            log.info(
                "is_eos_utility_present failed with error : {}".format(error))
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
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.backup_or_restore_files.__name__,
                error))
            return False, error


################################################################################
# command execution
################################################################################
    def run_remote_cmd(cmd, host, u_name, u_password, read_lines = True, read_nbytes = -1, **kwargs
                       ) -> Tuple[Union[List[str], str, bytes], bool]:
        """
        Execute any command on remote machine using paramiko instance.
        ref: https://stackoverflow.com/questions/28485647/wait-until-task-is-completed-on-remote-machine-through-python
        :param client_obj: client connection object to execute commands on remote machine.
        :type client_obj: Connection object.
        :param cmd: command to be executed on the client machine.
        :type cmd: str.
        :param time_out: command to be executed on the client machine.
        :type time_out: int seconds.
        :return: ([result/err], True/False).
        :rtype: tuple.
        """
        try:
            if not host:
                raise ValueError(const.MISSING_REQ_PARA.format(host))
            if not u_name:
                raise ValueError(const.MISSING_REQ_PARA.format(u_name))
            if not u_password:
                raise ValueError(const.MISSING_REQ_PARA.format(u_password))
            if not cmd:
                raise ValueError(const.MISSING_REQ_PARA.format(cmd))
            log.debug("Connect details: Host:%s, user name:%s, password:%s, port:%s",
                         host, u_name, u_password, port)
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            log.debug("Command: %s" % str(cmd))
            stdin, stdout, stderr = client.exec_command(cmd, timeout=time_out)
            exit_status = stdout.channel.recv_exit_status()
            if read_lines:
                result = stdout.readlines()
                result = [r.strip().strip("\n").strip() for r in result]
                log.debug("Result: %s" % str(result))
                error = stderr.readlines()
                error = [r.strip().strip("\n").strip() for r in error]
                log.debug("Error: %s" % str(error))
            else:
                result = stdout.read(read_nbytes)
            log.debug(exit_status)
            if exit_status != 0:
                if error:
                    raise IOError(error)
                raise IOError(result)
            client.close()
        except AuthenticationException as error:
                    log.error(const.EXCEPTION_MSG.format(CommonLib.connect.__name__, error))
        except SSHException as error:
                    log.error(const.EXCEPTION_MSG.format(CommonLib.connect.__name__, error))
        except (paramiko.SSHException, BaseException) as error:
            log.error(const.EXCEPTION_MSG.format(CommonLib.run_remote_cmd.__name__, error))
            return str(error), False

        return result, True

    def run_local_cmd(cmd: cmd = None
                      ) -> Tuple[bool, Union[List[str], str, bytes]]:
        """
        Execute any given command on local machine.
        :param cmd: command to be executed.
        :type cmd: str.
        :return: True/False, Success/str(err)
        :rtype: tuple.
        """
        try:
            if not cmd:
                raise ValueError(const.MSG_INVALID.format("command", cmd))
            log.info("Command: %s", cmd)
            proc = Popen(cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
            output, error = proc.communicate()
            log.info("output = %s", str(output))
            if const.MSG_RSA_KEY_ADDED in output:
                return True, output
            if const.LCMD_NOT_FOUND in error or error:
                return False, error
        except (CalledProcessError, BaseException) as error:
            log.error(const.EXCEPTION_MSG.format(CommonLib.run_local_cmd.__name__, error))
            return False, str(error)

        return True, output
    