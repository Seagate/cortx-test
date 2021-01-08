import pytest
import logging
from commons.utils import system_utils
from commons.helpers.node_helper import NodeHelper
from commons.helpers.health_helper import HealthHelper
def test_system_utils():
    system_utils.run_remote_cmd("pwd","10.237.65.202","root","seagate")
    system_utils.run_local_cmd('dir') 
    system_utils.is_path_exists('/home')
    system_utils.is_path_exists("C:\\Users\\532698\\Documents\\EOS\\workspace\\eos-test\\eos_test\\utility")
    system_utils.open_empty_file("C:\\Users\\532698\\Documents\\a.txt")
    system_utils.listdir("C:\\Users\\532698\\Documents\\EOS\\workspace\\eos-test\\eos_test\\utility")
    system_utils.makedir()

def test_node_helper():
    x = NodeHelper("10.237.65.202","root","seagate")
    x.execute_cmd('pwd')
    x.is_dir_exists('/root','hw_cfg')
    x.makedir('/root/','test')

def test_health_helper():
    x = HealthHelper("10.237.65.202","root","seagate")
    x.get_ports_of_service('csm') 
    x.get_ports_for_firewall_cmd('csm')   
    x.get_disk_usage('/root')
    x.get_system_cpu_usage()
    x.disk_usage_python_interpreter_cmd('/root')
    x.pcs_status_grep('csm')
    x.pcs_resource_cleanup()
    x.is_mero_online()
    x.is_machine_already_configured()
    x.all_cluster_services_online()