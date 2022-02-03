import requests

from commons.helpers.health_helper import Health
from commons.utils import system_utils as sysutils


def main():
    """
    Setup VM
    """
    print("STARTED: Setup Module operations.")
    hlth_master_list = []

    host = "ssc-vm-rhev4-1901.colo.seagate.com"
    username = "root"
    password = "seagate"
    hlth_master_list.append(Health(hostname=host, username=username, password=password))

    # print("Running cleanup_deploy.sh")
    # hlth_master_list[0].execute_cmd(cmd="sed -i -e 's/\r$//' /root/cleanup_deploy.sh")
    # cmd = f"/root/cleanup_deploy.sh /root/v20/cortx-k8s/k8_cortx_cloud "  \
    #       f"ssc-vm-rhev4-1902.colo.seagate.com" \
    #       f" ssc-vm-rhev4-1903.colo.seagate.com ssc-vm-rhev4-1904.colo.seagate.com " \
    #       f"ssc-vm-g2-rhev4-2899.colo.seagate.com ssc-vm-g2-rhev4-2920.colo.seagate.com " \
    #       f"/dev/sdb > cleanup_deploy.log"
    # hlth_master_list[0].execute_cmd(cmd=cmd, read_lines=True)

    print("Successfully done deployment")
    sysutils.run_local_cmd(cmd="export ADMIN_USR='cortxadmin'")
    sysutils.run_local_cmd(cmd="export ADMIN_PWD='Cortxadmin@123'")
    sysutils.run_local_cmd(cmd="export Target_Node='apurwa_1901'")
    sysutils.run_local_cmd(cmd="python3.7 scripts/cicd_k8s/client_multinode_conf.py "
                               "--master_node 'ssc-vm-rhev4-1901.colo.seagate.com' "
                               "--password 'seagate'")
    print("Create s3 account with name %s", "apurwa_s3")
    response = requests.post(url='https://ssc-vm-rhev4-1903.colo.seagate.com:31169/api/v2/login',
                             json={"username": "cortxadmin", "password": "Cortxadmin@123"},
                             verify=False)

    b_token = response.headers["Authorization"]

    resp = requests.post(url='https://ssc-vm-rhev4-1903.colo.seagate.com:31169/api/v2/s3_accounts',
                         json={"account_name": "s3account1", "account_email":
                               "s3account1@seagate.com", "password": "S3acc@123"},
                         headers={"Authorization": b_token, "Accept": "application/json"},
                         verify=False)

    access_key = resp.json()['access_key']
    secret_key = resp.json()['secret_key']

    sysutils.run_local_cmd(cmd="aws configure set plugins.endpoint awscli_plugin_endpoint")
    sysutils.run_local_cmd(cmd="aws configure set s3.endpoint_url https://s3.seagate.com")
    sysutils.run_local_cmd(cmd="aws configure set s3api.endpoint_url https://s3.seagate.com")
    sysutils.run_local_cmd(
        cmd="aws configure set default.ca_bundle /etc/ssl/stx-s3-clients/s3/ca.crt")
    sysutils.run_local_cmd(cmd=f"aws configure set aws_access_key_id {access_key}")
    sysutils.run_local_cmd(cmd=f"aws configure set aws_secret_access_key {secret_key}")
    sysutils.run_local_cmd(cmd="aws configure set default.region US")
    sysutils.run_local_cmd(cmd="aws configure set default.output json")
    print("Successfully done setup")


if __name__ == "__main__":
    main()
