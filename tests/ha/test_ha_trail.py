import pytest
from config import CMN_CFG
from commons.helpers.node_helper import Node
from libs.ha.ha_common_libs import HALibs

class TestHATrial:
    def setup_class(self):
        #runs onces for a class
        self.hostname =  CMN_CFG["nodes"][0]["hostname"]
        self.user = CMN_CFG["nodes"][0]["username"]
        self.password = CMN_CFG["nodes"][0]["password"]
        self.node_obj = Node(self.hostname, self.user, self.password)
        self.ha_obj = HALibs()
    def setup_method(self):
        #run everytime test is called
        print("Setup method")

    def teardown_method(self):
        # everytime after the test
        print("teadwon method")

    def teardown_class(self):
        print("Teardown class")

    def test_1(self):
        "Randowm ts"
        print("Running test")

        print("hostname: " + self.hostname)
        print("hostname: " + self.user)
        print("hostname: " + self.password)
        assert True

        response = self.node_obj.execute_cmd("pwd", read_lines=True)
        print(response)

        print("test completed")
