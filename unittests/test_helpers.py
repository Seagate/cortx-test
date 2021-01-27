"""
This file consists of unit tests for the methods in helper files
"""

import pytest
import logging
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from commons.helpers.bmc_helper import Bmc
from commons.helpers.telnet_helper import Telnet
from commons.helpers.controller_helper import ControllerLib


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
    x.is_motr_online()
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


@pytest.mark.skip
def test_controller_helper():
    x = ControllerLib(host="sm8-r19.pun.seagate.com", h_user="root",
                      h_pwd="seagate", enclosure_ip="10.0.0.2",
                      enclosure_user="manage", enclosure_pwd="Seagate123$")
    stat, mc_v, mc_s = x.get_mc_ver_sr()
    pswd = x.get_mc_debug_pswd(mc_v, mc_s)
    x.simulate_fault_ctrl(pswd, 0, "left", "psu", "e", "a")
    telnet_file = "test_telnet.xml"
    x.show_disks(telnet_file)
    count = x.get_total_drive_count(telnet_file)
    stat, health = x.check_phy_health("7", telnet_file)
    stat, health = x.set_drive_status_telnet(enclosure_id=0,
                                             controller_name="A",
                                             drive_number=7, status="disabled")
    stat = x.clear_drive_metadata(7)
    stat, health = x.set_drive_status_telnet(enclosure_id=0,
                                             controller_name="A",
                                             drive_number=7, status="enabled")
    stat, d = x.get_show_volumes()
    stat, d = x.get_show_expander_status()
    stat, d = x.get_show_disk_group()
    stat, d = x.get_show_disks()
