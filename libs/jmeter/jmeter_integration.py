import string
import os
import logging
from commons.commands import JMX_CMD
from commons.utils import system_utils
from config import CSM_REST_CFG

class JmeterInt():
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.jmeter_path = "/root/apache-jmeter-5.4/bin"
        self.jmx_path = "scripts/jmx_files" 
        self.jtl_self.jtl_log_path = "log/jmeter/"

    def verify_log(self, log_file):
        with open(log_file) as fp:
            content = fp.read()
        self.log.info(content)

    def run_jmx(self, jmx_file):
        #jmeter -n -t <test JMX file> -l <test log file> -e -o <Path to output folder>
        content = {"test.environment.hostname":CSM_REST_CFG["mgmt_vip"],
                   "test.environment.port":CSM_REST_CFG["port"],
                   "test.environment.protocol":"https",
                   "test.environment.adminuser":CSM_REST_CFG["csm_admin_user"]["username"],
                   "test.environment.adminpswd":CSM_REST_CFG["csm_admin_user"]["password"]}
        self.log.info("Updating : %s ", content)
        resp  = self.update_user_properties(content)
        if not resp:
            return False, "Failed to update the file."

        self.log.info(self.parse_user_properties())
        jmx_file_path = os.path.join(self.jmx_path,jmx_file)
        self.log.info("JMX file : %s", jmx_file_path)
        log_file = jmx_file.split(".")[0] + ".jtl"
        log_file_path = os.path.join(self.jtl_log_path, log_file)
        self.log.info("Log file name : %s ", log_file_path)
        cmd = JMX_CMD.format(self.jmeter_path, jmx_file_path, log_file_path, self.jtl_log_path)
        self.log.info("JMeter command : %s", cmd)
        resp = system_utils.run_local_cmd(cmd)
        self.verify_log(log_file_path)
        return resp
    
    def update_user_properties(self, content:dict):
        result = False
        try:
            lines = self.read_user_properties()
            counter = len(lines) + 1
            for key, value in content.items():
                key=key.translate({ord(c): None for c in string.whitespace})
                if type(value) is str:
                    value=value.translate({ord(c): None for c in string.whitespace})
                updated = False
                for index, line in enumerate(lines):
                    if key in line:
                        lines[index] = key + " = " + str(value) + "\n"
                        updated = True
                if not updated:
                    lines.append(key + " = " + str(value) + "\n")
                    counter = counter + 1

            fpath = os.path.join(self.jmeter_path, "user.properties")
            with open(fpath,'w') as fp
                self.log.info("Writing : %s", lines)
                fp.writelines(lines)
            read_lines = self.read_user_properties()
            return read_lines == lines
        except:
            self.log.error("Failed in updating the file")
        return result

    def parse_user_properties(self):
        lines = self.read_user_properties()
        dict = {}
        for line in lines:
            if line[0] != "#" and "=" in line:
                k,v = line.split("=")
                k=k.translate({ord(c): None for c in string.whitespace})
                v=v.translate({ord(c): None for c in string.whitespace})
                dict.update({k:v})
        return dict

    def read_user_properties(self):
        fpath = os.path.join(self.jmeter_path, "user.properties")
        with open(fpath) as stream:
            lines = stream.readlines()
        return lines