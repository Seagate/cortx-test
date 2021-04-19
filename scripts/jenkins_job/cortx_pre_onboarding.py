# -*- coding: utf-8 -*-
import configparser
import os
import unittest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from scripts.jenkins_job import gui_element_locators as loc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from commons.helpers.node_helper import Node

config_file = 'scripts/jenkins_job/config.ini'
config = configparser.ConfigParser()
config.read(config_file)


class CSMBoarding(unittest.TestCase):
    def setUp(self):
        # self.driver = webdriver.Firefox()
        chrome_options = Options()
        chrome_options.add_argument('--ignore-ssl-errors=yes')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(30)
        self.csm_mgmt_ip = os.getenv('CSM_MGMT_IP')
        self.admin_user = os.getenv('ADMIN_USR', config['preboarding']['username'])
        self.admin_pwd = os.getenv('ADMIN_PWD', config['preboarding']['password'])
        self.host_passwd = os.getenv('HOST_PASS')
        self.create_admin_user = True
        check_admin_user_cmd = "cat /etc/passwd | grep admin"
        nd_obj = Node(hostname=self.csm_mgmt_ip, username="root", password=self.host_passwd)
        response = nd_obj.execute_cmd(cmd=check_admin_user_cmd)
        if "/opt/seagate/users/admin" in str(response):
            self.create_admin_user = False

    def test_preboarding(self):
        try:
            if self.create_admin_user:
                browser = self.driver
                preboarding_url = config['preboarding']['url'].format(self.csm_mgmt_ip)
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
                ele.send_keys(config['preboarding']['email'])
                ele = self.get_element(By.ID, loc.Preboarding.create_btn)
                ele.click()
                ele = self.get_element(By.ID, loc.Preboarding.userlogin_ip)
                print("Admin user is created")
                print("Username: {} \nPassword: {}".format(self.admin_user, self.admin_pwd))
            else:
                print("Admin user already present. Skipping Preboarding")
        except:
            self.assertTrue(False, "Failed to create Admin User")

    def test_onboarding(self):
        try:
            browser = self.driver
            onboarding_url = config['onboarding']['url'].format(self.csm_mgmt_ip)
            browser.get(onboarding_url)
            ele = self.get_element(By.ID, loc.Onboarding.username_ip)
            self.clear_send(ele, self.admin_user)
            ele = self.get_element(By.ID, loc.Onboarding.password_ip)
            self.clear_send(ele, self.admin_pwd)
            ele = self.get_element(By.ID, loc.Onboarding.login_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.sys_ip)
            self.clear_send(ele, config['onboarding']['system'])
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.dns_server_ip)
            self.clear_send(ele, config['onboarding']['dns'])
            ele = self.get_element(By.ID, loc.Onboarding.dns_search_ip)
            self.clear_send(ele, config['onboarding']['search'])
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.ntp_server_ip)
            self.clear_send(ele, config['onboarding']['ntp'])
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.XPATH, loc.Onboarding.skip_step_chk)
            ele.click()
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.XPATH, loc.Onboarding.continue_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.confirm_btn)
            ele.click()
            ele = self.get_element(By.ID, loc.Onboarding.finish_btn)
            ele.click()
            print("Onboarding completed!")
        except:
            self.assertTrue(False, "Onboarding Failed")

    def get_element(self, by, loc):
        time.sleep(2)
        ele = WebDriverWait(self.driver, 60).until(EC.presence_of_element_located((by, loc)))
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

if __name__ == "__main__":
    unittest.main()
