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
"""CSM Pre boarding automated functions."""
import configparser
import os
import unittest
import time
import paramiko
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from scripts.jenkins_job import gui_element_locators as loc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from commons import pswdmanager


config_file = 'scripts/jenkins_job/config.ini'
config = configparser.ConfigParser()
config.read(config_file)


class CSMBoarding(unittest.TestCase):
    def setUp(self):
        chrome_options = Options()
        chrome_options.add_argument('--ignore-ssl-errors=yes')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(30)
        self.csm_mgmt_ip = os.getenv('MGMT_VIP')
        self.default_username = pswdmanager.decrypt(
            config['csmboarding']['username'])
        self.default_password = pswdmanager.decrypt(
            config['csmboarding']['password'])
        self.admin_user = os.getenv('ADMIN_USR', self.default_username)
        self.admin_pwd = os.getenv('ADMIN_PWD', self.default_password)
        self.host_passwd = os.getenv('HOST_PASS')
        self.usr = "root"


    def test_preboarding(self):
        '''
        result = config_chk.preboarding(self.admin_user, self.admin_pwd, self.admin_pwd)
        if result:
            print("Preboarding is done")
        else:
            self.assertTrue(False, "Failed to create Admin User")
        '''
        try:
            browser = self.driver
            preboarding_url = config['csmboarding']['preboarding_url'].format(
                self.csm_mgmt_ip)
            browser.get(preboarding_url)
            ele = self.get_element(By.ID, loc.Preboarding.start_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Preboarding.terms_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Preboarding.accept_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Preboarding.username_ip)
            ele.send_keys(self.admin_user)
            ele = self.get_element(By.ID, loc.Preboarding.password_ip)
            ele.send_keys(self.admin_pwd)
            ele = self.get_element(By.ID, loc.Preboarding.confirmpwd_ip)
            ele.send_keys(self.admin_pwd)
            ele = self.get_element(By.ID, loc.Preboarding.email_ip)
            ele.send_keys(config['csmboarding']['email'])
            ele = self.get_element(By.ID, loc.Preboarding.create_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Preboarding.userlogin_ip)
            self.driver.save_screenshot("".join(["Success-Preboarding-Screenshot",
                                                 str(time.strftime("-%Y%m%d-%H%M%S")), ".png"]))
            print("Admin user is created")
            print(
                "Username: {} \nPassword: {}".format(
                    self.admin_user,
                    self.admin_pwd))
        except BaseException:
            self.driver.save_screenshot("".join(["Failure-Preboarding-Screenshot",
                                                 str(time.strftime("-%Y%m%d-%H%M%S")), ".png"]))
            self.assertTrue(False, "Failed to create Admin User")


    def test_onboarding(self):
        try:
            browser = self.driver
            onboarding_url = config['csmboarding']['onboarding_url'].format(
                self.csm_mgmt_ip)
            browser.get(onboarding_url)
            ele = self.get_element(By.ID, loc.Onboarding.username_ip)
            self.clear_send(ele, self.admin_user)
            ele = self.get_element(By.ID, loc.Onboarding.password_ip)
            self.clear_send(ele, self.admin_pwd)
            ele = self.get_element(By.ID, loc.Onboarding.login_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.sys_ip)
            self.clear_send(ele, config['csmboarding']['system'])
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            #ele = self.get_element(By.XPATH, loc.Onboarding.ssl_choose_file)
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.dns_server_ip)
            self.clear_send(ele, config['csmboarding']['dns'])
            ele = self.get_element(By.ID, loc.Onboarding.dns_search_ip)
            self.clear_send(ele, config['csmboarding']['search'])
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.ntp_server_ip)
            self.clear_send(ele, config['csmboarding']['ntp'])
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.XPATH, loc.Onboarding.skip_step_chk)
            ele.click()
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            time.sleep(10)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.confirm_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.finish_btn)
            ele.click()
            self.driver.save_screenshot("".join(["Success-Onboarding-Screenshot",
                                                 str(time.strftime("-%Y%m%d-%H%M%S")), ".png"]))
            print("Onboarding completed!")
        except BaseException:
            self.driver.save_screenshot("".join(["Failure-Onboarding-Screenshot",
                                                 str(time.strftime("-%Y%m%d-%H%M%S")), ".png"]))
            self.assertTrue(False, "Onboarding Failed")

    def get_element(self, by, loc):
        time.sleep(2)
        ele = WebDriverWait(
            self.driver, 60).until(
            EC.presence_of_element_located(
                (by, loc)))
        return ele

    def clear_send(self, ele, txt):
        time.sleep(2)
        ele.click()
        ele.send_keys(Keys.CONTROL + "a")
        ele.send_keys(Keys.DELETE)
        ele.send_keys(txt)

    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException as e:
            return False
        return True

    def remote_execution(self, host, user, password, cmd, read_lines=False):
        """
        Execute any command on remote machine/VM
        :param host: Host IP
        :param user: Host user name
        :param password: Host password
        :param cmd: command user wants to execute on host
        :param read_lines: Response will be return using readlines() else using read()
        :return: response
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, username=user, password=password)
            stdin, stdout, stderr = client.exec_command(cmd)
            if read_lines:
                result = stdout.readlines()
            else:
                result = str(stdout.read())
            client.close()
            print(f"Response: {result}, Error: {stderr.readlines()}")
            return result
        except BaseException as error:
            print(error)
            return error


if __name__ == "__main__":
    unittest.main()
