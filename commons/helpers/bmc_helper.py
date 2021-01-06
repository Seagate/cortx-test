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
            cmd = f"ipmitool -I lanplus -H {bmc_ip} -U {bmc_user} -P {bmc_pwd} chassis power status"
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