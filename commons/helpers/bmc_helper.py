from commons.host import Host

class BmcHelper(Host):
    def connect_bmc():
        result = self.connect()
        if result:
            print("connection is establish")
    def get_bmc_ip(self) -> str:
        """
        Execute 'ipmitool lan print' on primary node and return bmc ip.
        :param host: primary node host.
        :type host: IP
        :param username: primary node username.
        :type username: str.
        :param password: primary node password.
        :type password: str.
        :return: bmc ip or none
        :rtype: str.
        """

        bmc_ip = None
        try:
            cmd = dest_cons.CMD_LAN_INFO
            logger.info(f"Running command {cmd}")
            status, response = self.host_obj.execute_cmd(cmd=cmd,read_lines=False
                                                        read_nbytes=ras_cons.BYTES_TO_READ,
                                                        , shell=False)
            response = response.decode("utf-8") if isinstance(response, bytes) else response
            logger.debug(response)
            for res in response.split("\n"):
                if "IP Address" in res and "IP Address Source" not in res:
                    bmc_ip = res.split(":")[-1].strip()
                    break
            logger.debug(f"BMC IP: {bmc_ip}")
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    FaultUtility.get_bmc_ip.__name__,
                    error))

        return bmc_ip

    def bmc_node_power_status(self, bmc_ip, bmc_user, bmc_pwd):
        """
        Function to check node power states using BMC
        :param bmc_ip: Node BMC IP
        :param bmc_user: Node BMC user name
        :param bmc_pwd: Node BMC user pwd
        :return: bool, resp
        :rtype: tuple
        """
        if not self.execute_cmd("rpm  -qa | grep ipmitool")[0]:
            logger.debug("Installing ipmitool")
            self.execute_cmd("yum install ipmitool")
        try:
            cmd = f"ipmitool -I lanplus -H {self.hostname} -U {self.username} -P {self.password} chassis power status"
            if not cmd:
                return False, "Command not found"
            logger.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            logger.debug("Output:", resp)
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.bmc_node_power_status.__name__,
                    error))
            return False, error

        logger.info(f"Successfully executed cmd {cmd}")
        return resp

    def bmc_node_power_on_off(self, bmc_ip, bmc_user, bmc_pwd, status="on"):
        """
        Function to on and off node power using BMC IP
        :param bmc_ip:
        :param bmc_user:
        :param bmc_pwd:
        :param status:
        :return:
        """
        if not self.execute_cmd("rpm  -qa | grep ipmitool")[0]:
            logger.debug("Installing ipmitool")
            self.execute_cmd("yum install ipmitool")
        cmd = f"ipmitool -I lanplus -H {bmc_ip} -U {bmc_user} -P {bmc_pwd} chassis power {status.lower()}"
        try:
            if not cmd:
                return False, "Command not found"
            logger.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            logger.debug("Output:", resp)
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.bmc_node_power_on_off.__name__,
                    error))
            return False, error

        logger.info(f"Successfully executed cmd {cmd}")
        return resp