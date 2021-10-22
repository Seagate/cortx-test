import logging
import pytest
import json
import time
from config import CMN_CFG
from commons.helpers.node_helper import Node

LOGGER = logging.getLogger(__name__)


class TestHA:
    @classmethod
    def setup_class(cls):
        cls.node_list = []
        for node in range(len(CMN_CFG["nodes"])):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)
            cls.node_list.append(cls.node_obj)

    def test_ha(self):
        print("Running test:Master Node")
        print("hostname: " + CMN_CFG["nodes"][0]["hostname"])
        print("password: " + CMN_CFG["nodes"][0]["password"])
        print("user: " + CMN_CFG["nodes"][0]["username"])
        print("Running test: Worker Node 1")
        print("hostname: " + CMN_CFG["nodes"][1]["hostname"])
        print("password: " + CMN_CFG["nodes"][1]["password"])
        print("user: " + CMN_CFG["nodes"][1]["username"])
        print("Running test: Worker Node 2")
        print("hostname: " + CMN_CFG["nodes"][2]["hostname"])
        print("password: " + CMN_CFG["nodes"][2]["password"])
        print("user: " + CMN_CFG["nodes"][2]["username"])
        print("***** Test Case 1 : shutdown node and publish event  *******")
        '''try:
            print("Shutdown down the node...")
            response1 = self.node_list[1].shutdown_node()
            print(response1)
        except:
            print("An exception occured")'''
        try:
            print("pre-condition: subscribe.py, publish.py, test_receiver.py, daemon.py should be available in Cortx Stack root dirctory \n")
            response1 = self.node_list[0].execute_cmd("/root/subscribe.py")
            LOGGER.info(response1)
            print("1." + response1.decode("utf-8").strip() + " Subscribe event successfully")
            print("\n 2. Running test_receiver.py in background and Waiting for event to publish...")
            response3 = self.node_list[0].execute_cmd("python /root/daemon.py")
            print(response3.decode("utf-8").strip())
            print("3. Shutdown down the node...")
            response1 = self.node_list[1].shutdown_node()
            print(response1)
            print("\n 4. Publishing  the event... \n")
            response2 = self.node_list[0].execute_cmd("/root/publish.py")
            print(response2.decode("utf-8").strip())
            print("\n Publish event successfully")
            print("\n 5. Event Message printing... \n")
            response4 = self.node_list[0].execute_cmd("cat /root/file.txt")
            print(response4.decode("utf-8").strip())
            print("\n Event Message printed successfully")
            print("\n 6. Killng process test reciever...")
            response2 = self.node_list[0].execute_cmd("pkill -f /root/test_receiver.py")
            print(response2.decode("utf-8").strip())
            print("Killed test_receiver successfully")
            print("\n 7. Removing pidfile...")
            response2 = self.node_list[0].execute_cmd("rm -f /root/pidfile")
            print(response2.decode("utf-8").strip())
            print("Removed pidfile successfully")
        except Exception as error:
            print(error)
            assert False
        assert True
