import pytest
import logging
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from commons.helpers.bmc_helper import Bmc

def test_node_helper():
    x = Node("10.237.65.202","root","seagate")
    x.get_authserver_log("/var/log/seagate/auth/server/app.log")
    x.send_systemctl_cmd("stop",["s3authserver"])
    x.status_service(["s3authserver"],"active")
    x.send_systemctl_cmd("start",["s3authserver"])
    x.path_exists('/root')
    x.path_exists('/rt')
    x.create_file('tmp.txt',34)
    x.rename_file('tmp.txt','dk.txt')
    x.remove_file('dk.txt')
    x.list_dir('/root')
    x.make_dir('/root/test_dk')
    x.path_exists('/root/test_dk')
    x.remove_dir('/root/test_dk')
    x.create_dir_sftp('/root/test_dk')
    x.delete_dir_sftp('/root/test_dk')
    x.execute_cmd('pwd')

    
def test_health_helper():
    x = Health("10.237.65.202","root","seagate")
    x.get_ports_of_service('csm')
    x.get_ports_for_firewall_cmd('csm')
    x.get_disk_usage('/root',field_val=3)
    x.get_disk_usage('/root',field_val=2)
    x.get_disk_usage('/root',field_val=1)
    x.get_disk_usage('/root',field_val=0)
    x.get_cpu_usage()
    x.get_memory_usage()
    x.get_pcs_service_systemd('csm')
    x.pcs_status_grep('csm')
    x.pcs_resource_cleanup()
    x.is_mero_online()
    x.is_machine_already_configured()
    x.all_cluster_services_online()


def test_bmc_helper():
    x = Bmc(hostname="sm7-r19.pun.seagate.com", username="root", password="seagate")
    x.get_bmc_ip()
    x.bmc_node_power_status('10.237.65.16', 'bmcadmin', 'adminBMC!')
    x.bmc_node_power_on_off('10.237.65.16', 'bmcadmin', 'adminBMC!')
    x.set_bmc_ip('10.237.65.16')
    x.create_bmc_ip_change_fault('10.234.56.9')
    x.resolve_bmc_ip_change_fault('10.237.65.16')
