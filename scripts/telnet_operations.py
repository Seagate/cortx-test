import logging
import telnetlib
import time
import os
import subprocess

LOGGER = logging.getLogger(__name__)


class TelnetOperations:
    """
    This class includes functions for telnet operations which are needed to
    be performed from node.
    """

    def get_mc_ver_sr(self, enclosure_ip, enclosure_user, enclosure_pwd, cmd):
        """
        Function to get the version and serial number of the management
        controller
        :param enclosure_ip: IP of the enclosure
        :type: str
        :param enclosure_user: Username of the enclosure
        :type: str
        :param enclosure_pwd: Password of the enclosure
        :type: str
        :param cmd: Command to be run on telnet session
        :type: str
        :return: version and serial number of the management controller
        :rtype: Boolean, Strings
        """
        tn = telnetlib.Telnet(host=enclosure_ip)

        try:
            output = tn.read_until(b"login: ", 15)
            tn.write(enclosure_user.encode() + b"\r\n")

            tn.read_until(b"Password: ", 15)
            tn.write(enclosure_pwd.encode() + b"\r\n")
            time.sleep(5)

            LOGGER.info(f"Running command {cmd}")
            tn.write(cmd.encode() + b"\r\n")
            time.sleep(5)
            out = tn.read_very_eager()
            LOGGER.info(out)
            tn.write(b"exit\r\n")
            time.sleep(10)
            LOGGER.info("Telnet Connection closed")
        except Exception as e:
            LOGGER.info(f"{e.__class__} occurred")
            return False, e

        f = open('temp.txt', 'wb')
        fw = f.write(output)
        f.close()

        mc_ver = os.popen("sed '/MC Version/!d' temp.txt | awk '{print "
                          "$NF}'").read()

        mc_sr = os.popen("sed '/Serial Number/!d' temp.txt | awk '{print "
                         "$NF}'").read()
        os.remove('temp.txt')

        return True, mc_ver, mc_sr

    def simulate_fault_ctrl(self, mc_deb_password, enclosure_ip, telnet_port,
                            timeout, cmd):
        """
        Function to simulate faults on the controller
        :param mc_deb_password: Password of Management controller debug console
        :type: str
        :param enclosure_ip: IP of the enclosure
        :type: str
        :param telnet_port: Telnet port number for connecting to MC debug
        console
        :type: str
        :param timeout: Timeout value
        :type: str
        :param cmd: Command to be run on telnet session
        :type: str
        :return: Boolean, Response
        :rtype: Tuple of (bool, String)
        """
        try:
            tn = telnetlib.Telnet(host=enclosure_ip,
                                  port=telnet_port,
                                  timeout=int(timeout))

            read_str = tn.read_until(b"Password: ", 15)
            if read_str.decode() == "Password:":
                LOGGER.info("Entering the password")
                tn.write(mc_deb_password.encode())
                time.sleep(2)
                out = tn.read_very_eager()
                LOGGER.info(out)
                tn.write(b"\r\n\n\n")
                time.sleep(5)

                tn.write(b"\r\n\n")
                LOGGER.info(f"Running command {cmd}")
                tn.write(cmd.encode() + b"\r\n")
                tn.write(b"\r\n\n\n")
                LOGGER.info("Waiting for 15 seconds for alert generation")
                time.sleep(15)
                out = tn.read_very_eager()
                LOGGER.info(out)
                tn.write(b"exit\r\n")
                time.sleep(5)
                return True, read_str.decode()
            else:
                tn.close()
                return False, read_str.decode()
        except Exception as e:
            LOGGER.info(f"{e.__class__} occurred")
            return False, e

    def set_drive_status_telnet(
            self,
            enclosure_ip,
            username,
            pwd,
            status,
            cmd):
        """
        Enable or Disable drive status from disk group.
        :param enclosure_ip: IP of the Enclosure
        :type: str
        :param username: Username of the enclosure
        :type: str
        :param pwd: password for the enclosure user
        :type: str
        :param status: Status of the drive. Value will be enabled or disabled
        :type: str
        :param cmd: Command to be run on MC debug console
        :type: str
        :return: True/False, drive status
        :rtype: Boolean, string
        """
        tn = telnetlib.Telnet(host=enclosure_ip)

        try:
            tn.read_until(b"login: ", 15)
            tn.write(username.encode() + b"\r\n")

            tn.read_until(b"Password: ", 15)
            tn.write(pwd.encode() + b"\r\n")
            time.sleep(5)

            LOGGER.info(f"Running command {cmd}")

            out = tn.write(cmd.encode() + b"\r\n")
            time.sleep(5)
            if status == "Disabled":
                out = tn.write(b"y\r\n")
                time.sleep(5)

            LOGGER.info(out)
            tn.write(b"exit\r\n")
            time.sleep(10)
            LOGGER.info("Telnet Connection closed")
            return True, status
        except Exception as e:
            LOGGER.info(f"{e.__class__} occurred")
            return False, e

    def show_disks(self, enclosure_ip, enclosure_user, enclosure_pwd,
                   telnet_filepath, cmd):
        """
        Function to get the version and serial number of the management
        controller
        :param enclosure_ip: IP of the enclosure
        :type: str
        :param enclosure_user: Username of the enclosure
        :type: str
        :param enclosure_pwd: Password of the enclosure
        :type: str
        :param telnet_filepath: File path to save response of telnet command
        :type: str
        :param cmd: Command to be run on telnet session
        :type: str
        :return: True/False, Path of the telnet file
        :rtype: Boolean, String
        """
        try:
            command = "yum -y install sshpass"
            os.system(command)

            time.sleep(5)
            command = "sshpass -p {} ssh -o 'StrictHostKeyChecking no' {}@{} " \
                      "{}".format(enclosure_pwd, enclosure_user,
                                  enclosure_ip, cmd)

            resp = subprocess.call(command, stdout=open(telnet_filepath, 'w'),
                                   shell=True)
            return True, telnet_filepath
        except Exception as e:
            LOGGER.info(f"{e.__class__} occurred")
            return False, e

    def execute_cmd_on_enclosure(self,
                                 enclosure_ip,
                                 enclosure_user,
                                 enclosure_pwd,
                                 file_path,
                                 cmd):
        """
        Function to execute command on enclosure and save result into log file path.
        :param enclosure_ip: IP of the enclosure.
        :type: str
        :param enclosure_user: Username of the enclosure.
        :type: str
        :param enclosure_pwd: Password of the enclosure.
        :type: str
        :param file_path: File path to save response of telnet command.
        :type: str
        :param cmd: Supported commands by enclosure.
        :type: str
        :return: True/False, Path of the telnet file.
        :rtype: tuple.
        """
        try:
            command = "yum -y install sshpass"
            LOGGER.info(f"Command: {command}")
            os.system(command)
            time.sleep(5)
            command = "sshpass -p {} ssh -o 'StrictHostKeyChecking no' {}@{} " \
                      "{}".format(enclosure_pwd, enclosure_user,
                                  enclosure_ip, cmd)
            LOGGER.info(f"Execution command: {command}")
            status = subprocess.call(command, stdout=open(file_path, 'w'), shell=True)
            if status != 0:
                raise Exception("Execution failed.")
            if not os.path.exists(file_path):
                raise Exception(f"Log file path not exists: {file_path}")
            os.system("sed -i '1d; $d' {}".format(file_path))  # Added to remove first line from log.
            return True, file_path
        except Exception as err:
            LOGGER.error(f"Error occurred in {TelnetOperations.execute_cmd_on_enclosure.__name__}. Error: {err}")
            return False, err

    def clear_metadata(self, enclosure_ip, enclosure_user, enclosure_pwd, cmd):
        """
        Function to clear the metadata of given drive
        :param enclosure_ip: IP of the enclosure
        :type: str
        :param enclosure_user: Username of the enclosure
        :type: str
        :param enclosure_pwd: Password of the enclosure
        :type: str
        :param cmd: Command to be run on telnet session
        :type: str
        :return: version and serial number of the management controller
        :rtype: Boolean, Strings
        """
        tn = telnetlib.Telnet(host=enclosure_ip)

        try:
            tn.read_until(b"login: ", 15)
            tn.write(enclosure_user.encode() + b"\r\n")

            tn.read_until(b"Password: ", 15)
            tn.write(enclosure_pwd.encode() + b"\r\n")
            time.sleep(5)

            LOGGER.info(f"Running command {cmd}")
            tn.write(cmd.encode() + b"\r\n")
            time.sleep(5)
            tn.write(b"y\r\n")
            time.sleep(10)

            out = tn.read_very_eager()
            LOGGER.info(out)
            tn.write(b"exit\r\n")
            time.sleep(10)
            LOGGER.info("Telnet Connection closed")
        except Exception as e:
            LOGGER.info(f"{e.__class__} occurred")
            return False, e

        f = open('temp.txt', 'wb')
        fw = f.write(out)
        f.close()

        status = False
        string = "Success: Command completed successfully. " \
                 "- Metadata was cleared."
        with open('temp.txt', 'r') as read_obj:
            for line in read_obj:
                if string in line:
                    status = True

        os.remove('temp.txt')
        return status, out


def main(op):
    op = op.replace("\\", "")
    operation = TelnetOperations()
    response = eval("operation.{}".format(op))
    print(response)
    return response


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Telnet Operations')
    parser.add_argument('--telnet_op', dest='telnet_op', required=True,
                        help='Telnet operation to be performed')
    args = parser.parse_args()

    main(args.telnet_op)
