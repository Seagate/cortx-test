import pytest
import json
from config import CMN_CFG
from commons.helpers.node_helper import Node


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
        print("***** Test Case 3 : Delete pod forcefully and publish event  *******")
        try:
            print("pre-condition")
            response1 = self.node_list[0].execute_cmd("kubectl run tomcat --image tomcat:8.0")
            print("pre-condition satisfied")
            print("Step1: List the pod")
            response2 = self.node_list[0].execute_cmd("kubectl get pod", read_lines=True)
            print(response2)
            print("Step1 completed")
            print("Verify Pod Status")
            pod_name='tomcat'
            cmd = "kubectl get pods " + pod_name + " -o jsonpath={.status.phase}"
            response3 = self.node_list[0].execute_cmd(cmd, read_lines=True)
            res3 = str(response3)[2:-2]
            print(res3)
            if res3 == "Running":
                print("The status of pod is Running")
                try:
                    print("Step2: Delete the pod")
                    cmd = "kubectl delete pod " + pod_name + "--grace-period=0 --force"
                    response4 = self.node_list[0].execute_cmd(cmd, read_lines=True)
                    print(response4)
                    print("Deleted the pod sucessfully")
                except Exception as error:
                    print(error)
            elif res3 == "Pending":
                print("The status of pod is ContainerCreating")
            print("pre-condition: subscribe.py, publish.py, test_receiver.py, daemon.py should be available in Cortx Stack root dirctory \n")
            response1 = self.node_list[0].execute_cmd("/root/subscribe.py")
            print("1." + response1.decode("utf-8").strip() + " Subscribe event successfully")
            print("\n 2. Running test_receiver.py in background and Waiting for event to publish...")
            response3 = self.node_list[0].execute_cmd("python /root/daemon.py")
            print(response3.decode("utf-8").strip())
            print("\n Step3. Publishing  the event... \n")
            response2 = self.node_list[0].execute_cmd("/root/publish.py")
            print(response2.decode("utf-8").strip())
            print("\n Publish event successfully")
            print("\n Step4. Event Message printing... \n")
            response4 = self.node_list[0].execute_cmd("cat /root/file.txt")
            print(response4.decode("utf-8").strip())
            print("\n Event Message printed successfully")
            print("\n 3. Killng process test reciever...")
            response2 = self.node_list[0].execute_cmd("pkill -f /root/test_receiver.py")
            print(response2.decode("utf-8").strip())
            print("Killed test_receiver successfully")
            print("\n 4. Removing pidfile...")
            response2 = self.node_list[0].execute_cmd("rm -f /root/pidfile")
            print(response2.decode("utf-8").strip())
            print("Removed pidfile successfully")
        except Exception as error:
            print(error)
            assert False
        assert True

