
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
# Local libraries
################################################################################
class S3_helper(Node_Helper):

    def configure_s3cfg(self, access, secret, path=CM_CFG["s3cfg_path"]):
        """
        Function to configure access and secret keys in s3cfg file.
        :param access: aws access key
        :param secret: aws secret key
        :param path: path to s3cfg file
        :return: True
        """
        if self.execute_cmd("s3cmd --version"):
            res1 = self.update_config(path, "default", "access_key", access)
            res2 = self.update_config(path, "default", "secret_key", secret)
            res = res1 and res2
        else:
            msg = "S3cmd is not present, please install it and than run the " \
                  "configuration."
            log.warning(msg)
            res = False

        return res

    def configure_s3fs(self, access, secret, path=CM_CFG["s3fs_path"]):
        """
        Function to configure access and secret keys for s3fs.
        :param access: aws access key
        :param secret: aws secret key
        :param path: s3fs config file
        :return: True
        """
        if self.execute_cmd("s3fs --version") and os.path.exists(path):
            with open(path, "w+") as fd:
                fd.write(f"{access}:{secret}")
            res = True
        else:
            msg = "S3fs is not present, please install it and than run the " \
                  "configuration."
            log.info(msg)
            res = False

        return res

    def check_s3services_online(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Check whether all s3server services are online
        :return: False, if no s3server services found or are not Online
        :return: True, if all the s3server services are online
        :return: None, if any exception
        """
        try:
            output = self.remote_execution(
                host, user, pwd, cons.MERO_STATUS_CMD)
            s3services = []
            for line in output:
                if "s3server" in line:
                    s3services.append(line.strip())
            if s3services == []:
                return False, "No s3server service found!"
            for service in s3services:
                if not service.startswith("[started]"):
                    return False, s3services
            return True, s3services
        except BaseException as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.check_s3services_online.__name__,
                error))
            return False, error

    def get_s3server_service_status(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], shell=True):
        """
        Execute command to get status any system service at remote s3 server
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param service: Name of the service
        :return: response
        """
        result = self.remote_execution(
            host, user, pwd, cons.SYSTEM_CTL_STATUS_CMD.format(service),
            shell=shell)
        result_ = ''.join(result)
        log.info(result_.split())
        element = result_.split()
        if 'active' in element:
            return True, element
        else:
            return False, element


    def start_s3server_service(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Execute command to start any system service at remote s3 server
        :param service: Name of the service
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: response
        """
        return self.remote_execution(host, user, pwd,
                                     cons.SYSTEM_CTL_START_CMD.format(service))

    def stop_s3server_service(self, service, host=CM_CFG["host"],
                              user=CM_CFG["username"], pwd=CM_CFG["password"]):
        """
        Execute command to stop any system service at remote s3 server
        :param service: Name of the service
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: response
        """
        return self.remote_execution(host, user, pwd,
                                     cons.SYSTEM_CTL_STOP_CMD.format(service))

    def restart_s3server_service(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], shell=True):
        """
        Execute command to restart any system service at remote s3 server
        :param service: Name of the service
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: response
        """
        return self.remote_execution(
            host, user, pwd, cons.SYSTEM_CTL_RESTART_CMD.format(service),
            shell=shell)


    def restart_s3server_processes(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], wait_time=30):
        """
        Restart all s3server processes using hctl command
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param wait_time: Wait time in sec after restart
        :return:
        """
        try:
            fids = self.get_s3server_fids(host, user, pwd)
            for pid in fids:
                log.info("Restarting fid : {}".format(pid))
                self.remote_execution(host, user, pwd,
                                      cons.SYSTEM_CTL_RESTART_CMD.format(pid))
                time.sleep(wait_time)
            log.info(
                "Is mero online : {}".format(
                    self.is_mero_online(
                        host, user, pwd)))
            return True, fids
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.restart_s3server_processes.__name__,
                    error))
            return False, error

    def get_s3server_resource(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Get resources of all s3server instances using pcs command.
        :param str host: IP of the host
        :param str user: user name of the host
        :param str pwd: password for the user
        :return: response, list of s3 resources
        :rtype: list
        """
        output = self.remote_execution(
            host, user, pwd, cons.PCS_RESOURCE_SHOW_CMD)
        logger.info(f"Response: {output}")
        s3_rcs = []
        for line in output:
            if "s3server-c" in line:
                logger.info(line)
                fid = line.split()[0]
                s3_rcs.append(fid)
        return s3_rcs

    def restart_s3server_resources(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], wait_time=30, shell=True):
        """
        Restart all s3server resources using pcs command
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param wait_time: Wait time in sec after restart
        :param shell: for interactive shell True/False
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        try:
            rcs = self.get_s3server_resource(host, user, pwd)
            for rc in rcs:
                logger.info("Restarting resource : {}".format(rc))
                self.remote_execution(
                    host,
                    user,
                    pwd,
                    cons.PCS_RESOURCE_RESTART_CMD.format(rc),
                    shell=shell)
                time.sleep(wait_time)
            logger.info(
                "Is mero online : {}".format(
                    self.is_mero_online(
                        host, user, pwd)))
            return True, rcs
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.restart_s3server_resources.__name__,
                    error))
            return False, error

    def is_s3_server_path_exists(
            self,
            path,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], shell=True):
        """
        Check if file exists on s3 server
        :param path: Absolute path of the file
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :return: bool, response
        """
        try:
            client = self.connect(host, username=user, password=pwd,
                                  shell=shell)
            log.info("client connected")
            sftp = client.open_sftp()
            log.info("sftp connected")
            try:
                sftp.stat(path)
            except IOError as err:
                if err[0] == 2:
                    raise err
            sftp.close()
            client.close()
            return True, path
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.is_s3_server_path_exists.__name__,
                    error))
            return False, error

    def get_s3server_fids(self, host=CM_CFG["host"],
                          user=CM_CFG["username"], pwd=CM_CFG["password"]):
        """
        Get fid's of all s3server processes
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: response
        """
        output = self.remote_execution(host, user, pwd, cons.MERO_STATUS_CMD)
        log.info(f"Response: {output}")
        fids = []
        for line in output:
            if "s3server" in line:
                log.info(line)
                fid = "{}@{}".format(line.split()[2], line.split()[3])
                fids.append(fid)
        return fids

    def copy_s3server_file(
            self,
            file_path,
            local_path,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"],
            shell=True):
        """
        copy file from s3 server to local path
        :param file_path: Remote path
        :param local_path: Local path
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: bool, local path
        """
        try:
            client = self.connect(
                host, username=user, password=pwd, shell=shell)
            log.info("client connected")
            sftp = client.open_sftp()
            log.info("sftp connected")
            sftp.get(file_path, local_path)
            log.info("file copied to : {}".format(local_path))
            sftp.close()
            client.close()
            return True, local_path
        except BaseException as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.copy_s3server_file.__name__,
                error))
            return False, error

    def is_string_in_s3server_file(self, string, file_path):
        """
        find given string in file present on s3 server
        :param string: String to be check
        :param file_path: file path
        :return: Boolean
        """
        local_path = os.path.join(os.getcwd(), 'temp_file')
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            local_path = self.copy_s3server_file(file_path, local_path)[0]
            if string in open(local_path).read():
                log.info("Match found in : {}".format(file_path))
                return True, "Success"
            num = 1
            while True:
                if os.path.exists(local_path):
                    os.remove(local_path)
                local_path = self.copy_s3server_file(
                    file_path + '.' + str(num), local_path)[0]
                if string in open(local_path).read():
                    log.info(
                        "Match found in : {}".format(
                            file_path + '.' + str(num)))
                    return True, "Success"
                num = num + 1
                if num > 6:
                    break
            return False, "Not found"
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.is_string_in_s3server_file.__name__,
                    error))
            return None, error
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def enable_disable_s3server_instances(
            self,
            resource_disable=True,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], wait_time=1):
        """
        Enable or disable s3server instances using pcs command
        :param resource_disable: True for disable and False for enable
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param wait_time: Wait time in sec after resource action
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        try:
            rcs = self.get_s3server_resource()
            for rc in rcs:
                if resource_disable:
                    logger.info("Disabling resource : {}".format(rc))
                    self.remote_execution(
                        host, user, pwd, cons.PCS_RESOURCE_DISABLE_CMD.format(rc))
                    time.sleep(wait_time)
                else:
                    logger.info("Enabling resource : {}".format(rc))
                    self.remote_execution(
                        host, user, pwd, cons.PCS_RESOURCE_ENABLE_CMD.format(rc))
                    time.sleep(wait_time)
            logger.info(
                "Is mero online : {}".format(
                    self.is_mero_online(
                        host, user, pwd)))
            return True, rcs
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.enable_disable_s3server_instances.__name__,
                    error))
            return False, error

    def configure_minio(self, access, secret, path=CM_CFG["minio_path"]):
        """
        Function to configure minio creds in config.json file.
        :param access: aws access key
        :param secret: aws secret key
        :param path: path to minio cfg file
        :return: True/False
        """

        if os.path.exists(path):
            data = self.get_json(path)
            data["hosts"]["s3"]["accessKey"] = access
            data["hosts"]["s3"]["secretKey"] = secret
            res = self.update_json(path, data)
        else:
            msg = "Minio is not installed please install and than run the " \
                  "configuration"
            logger.warning(msg)
            res = False

        return res

    def get_local_keys(
            path=CM_CFG["aws_path"],
            section=CM_CFG["aws_cred_section"]):
        """
        Get local s3 access and secret keys
        :param path: credential file path
        :param section: section name for the profile
        :return:
        """
        if not os.path.exists(path) and os.path.isfile(path):
            raise cons.FILE_NOT_PRESENT_MSG.format(path)
        config = configparser.ConfigParser()
        config.read(path)
        access_key = config[section]["aws_access_key_id"]
        secret_key = config[section]["aws_secret_access_key"]
        log.info(f"fetched {access_key} access and {secret_key} secret key")
        return access_key, secret_key

    def is_string_in_file(self, string,file_path,shell=True):
        """
        find given string in file present on s3 server
        :param string: String to be check
        :param file_path: file path
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: Boolean
        """
        local_path = os.path.join(os.getcwd(), "temp_file")
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            response = self.copy_s3server_file(
                file_path, local_path, host=host, shell=shell)
            data = open(local_path).read()
            match = re.search(string, data)
            if match:
                log.info("Match found in : {}".format(file_path))
                return True, match
            else:
                return False, "String Not Found"
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(NodeHelper.is_string_in_file.__name__, error))
            return False, error
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)
