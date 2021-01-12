import pytest
import logging
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health

def test_node_helper():
    x = Node("10.237.65.202","root","seagate")
    x.execute_cmd('pwd')
    x.is_dir_exists('/root','hw_cfg')
    x.makedir('/root/','test')
    x.get_authserver_log("/var/log/seagate/auth/server/app.log")
    x.status_service(["s3authserver"],"active")
    x.start_stop_services(["s3authserver"],"stop_service")
    x.start_stop_services(["s3authserver"],"start_service")
    x.create_file('tmp',20)
    
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