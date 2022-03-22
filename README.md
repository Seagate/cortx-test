# cortx-test
CORTX-TEST is a repository for multiple automation projects developed for CORTX LR-R2 and future versions.

It is logically divided into following components: 
* Test Automation framework
* Execution Ecosystem
* Robot framework and
* Tools (reporting, DI, clone TP, etc.,).

## Getting Started
This document assumes that you are aware about Github and if you are coming from svn or other versioning system it is recommended to . Follow the link https://github.com/pranav-sahasrabudhe/cortx-test-1/blob/wip-readme-update/github-process-readme.md to configure git on your local machine. Following Readme document will give you enough insights and start contributing.

You can have a separate client VM with any Linux flavour to install client side pre-requisites and start using automation framework on the same VM. This VM should have connectivity to Cortx Cluster OR CORTX OVA deployment. Alternatively you may use one of the nodes as client (less recommended).     

## Git process
Typically a member contributing to test framework would follow the review process as follows:
1. We are following the concept of upstream and downstream where commits happen on your forked repository (downstream) 
2. Then you can raise a PR to merge it to Seagate Cortx-Test repository (Upstream). 
3. Moderators of Cortx-Test can create server side feature branch if multiple developers are working on same feature branch. 
4. Team member should be able to check-in and raise the PR to upstream even if they have read-only access to Seagate Repositories using this process. 

## Get the Sources
Fork local repository from Seagate's Cortx-Test repository and then clone Cortx-Test repository from Seagate repository. 
Commands as follows:
```
git clone https://github.com/Seagate/cortx-test.git
cd cortx-test/
git status
git branch
git checkout dev
git remote -v
git remote add upstream https://github.com/Seagate/cortx-test.git
git remote -v
```
Issuing the above command again will return output as shown:
```
> origin    https://github.com/YOUR_USERNAME/cortx-test.git (fetch)
> origin    https://github.com/YOUR_USERNAME/cortx-test.git (push)
> upstream        https://github.com/Seagate/cortx-test.git (fetch)
> upstream        https://github.com/Seagate/cortx-test.git (push)
```
Then fetch upstream...
```
git fetch upstream
git pull upstream dev
``` 

## Setting up dev environment
Following steps help in setting up client side env, where test framework will run. These steps assume that you have followed earlier process (i.e. git client is installed and `Cortx-test` is cloned)  
    
    1. `yum update -y`
    
    2. `yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make sqlite-devel`
    
    3. `cd /usr/src && wget https://www.python.org/ftp/python/3.7.9/Python-3.7.9.tgz && tar xzf Python-3.7.9.tgz && rm Python-3.7.9.tgz`
    
    4. `cd /usr/src/Python-3.7.9 && ./configure --prefix=/usr --enable-optimizations`
        
    5. `cd /usr/src/Python-3.7.9 && make altinstall`
    5a. Right here at this point you can check python is installed correctly by going in interactive mode. You can issue command "pip3 install pysqlite3" and type "import sqlite3" to confirm that sqlite3 is installed. This will save a lot of your time if you run into issues later for python installation. In some linux flavours you need --enable-loadable-sqlite-extensions switch to be added while configuring python.   
    cd /usr/src/Python-3.7.9 && ./configure --prefix=/usr --enable-optimizations --enable-loadable-sqlite-extensions
    
    6. Create a softlink to point to this installation. You can check the folder created and 
    improvise following command.
       `ln -s /usr/local/bin/python3.7 python3.7
    
    7. `yum install -y python3-devel librdkafka nfs-utils python3-tkinter`
    
    8. `python3.7 -m venv virenv`
    
    9. `source virenv/bin/activate` or use old style `. ./virenv/bin/activate`
      
    8. `pip install --upgrade pip`
    
    9. `pip install pysqlite3`
    
    10. Change dir to cortx-test project directory, make sure a requirement file is present in project dir. Use following command to install python packages.
    `pip install --ignore-installed -r requirements.txt`
    You can issue virenv/bin/deactivate to deactivate pyenv.
    
    11. Install awscli with default python 3.6 pre installed with inhouse vm images and 
    configure aws and copy cert file.
    
    Alternatively by skipping step 8 to 10, you can also set python environment by using virtual env.

## Steps to copy certificate
```
mkdir -p /etc/ssl/stx

mkdir -p /etc/ssl/stx-s3-clients/s3/

curl https://raw.githubusercontent.com/Seagate/cortx-s3server/kubernetes/scripts/haproxy/ssl/s3.seagate.com.crt -o /etc/ssl/stx-s3-clients/s3/ca.crt

curl https://raw.githubusercontent.com/Seagate/cortx-prvsnr/4c2afe1c19e269ecb6fbf1cba62fdb7613508182/srv/components/misc_pkgs/ssl_certs/files/stx.pem -o /etc/ssl/stx/stx.pem
```

## Script to set up client environment (Alternate option to manual steps)
Change dir to your local repository root folder. If you have checked out your code 
in clean_dev directory created in your home on Linux machine (RHEL Flavour), then
`/home/<yourname>/clean_dev` is the local repository root folder. 
```
 # cd clean_dev
 # ./cortx-test/ci_tools/client_setup.sh 
```
This script should handle client setup. However, note that python configures does not have switch --enable-loadable-sqlite-extensions in script.

## Steps to set up s3 client
To set up s3 client tools, make sure you have completed basic setup in `Set up dev environment`.  
Script in project's root folder cortx-test `scripts/s3_tools/Makefile` can be used to install s3 tools on client.
```commandline
Required arguments in configuration:
    ACCESS aws_access_key_id
    SECRET aws_secret_access_key
optional arguments:
    -i --ignore-errors  Ignore all errors in commands executed to remake files.
    -k --keep-going     Continue as much as possible after an error.
    --ENDPOINT=s3_endpoint
    --CA_CRT=certificate_file_path
    --NFS_SHARE=NFS_share_jclient_path
    --APACHE_J_METER=apache-jmeter-5.4.1.tgz
    --VERIFY_SSL='True' This is used to whether https/ssl be used or not
    --VALIDATE_CERTS='True' This is used whether given certificate should be verified or not.
    

make help --makefile=scripts/s3_tools/Makefile
    all           : Install & configure tools like aws, s3fs, s3cmd, minio, call in case it's a new machine. Eg: make all ACCESS=<new-accesskey> SECRET=<new-secretkey>
    clean         : Remove installed tools like aws, s3fs, s3cmd, minio. Eg: make clean
    install-tools : Install tools like aws, s3fs, s3cmd, minio, call in case it's a new machine. Eg: make install-tools
    configure-tools: Install tools like aws, s3fs, s3cmd, minio, call in case it's a new machine. Eg: make configure-tools ACCESS=<new-accesskey> SECRET=<new-secretkey>
    aws          : Install & configure aws tool. Eg: make aws ACCESS=<new-accesskey> SECRET=<new-secretkey>
    s3fs         : Install & configure s3fs tool. Eg: make s3fs ACCESS=<new-accesskey> SECRET=<new-secretkey>
    s3cmd        : Install & configure s3cmd tool. Eg: make s3cmd ACCESS=<new-accesskey> SECRET=<new-secretkey>
    jcloud-client: Setup jcloud-client. Eg: make jcloud-client
    minio        : Install & configure minio tool. Eg: make minio ACCESS=<new-accesskey> SECRET=<new-secretkey>
    s3bench-install: Setup s3bench tool. Eg: make s3bench-install --makefile=<makefile_path>"
	apache-jmeter-install: Setup apache-jmeter-install tool. Eg: make apache-jmeter-install --makefile=<makefile_path>"
    bashrc-configure : Configure ~/.bashrc for updating ulimit -n for allowing file descriptors 
    
To increase ulimit for allowing maximum file descriptors
make bashrc-configure

To install & configure all tools:
make all --makefile=scripts/s3_tools/Makefile ACCESS=<aws_access_key_id> SECRET=<aws_secret_access_key> ENDPOINT=<lb ipaddress> VALIDATE_CERTS=<Tree/False> VERIFY_SSL=<True/False>

To just configure installed tools:
make configure-tools --makefile=scripts/s3_tools/Makefile ACCESS=<aws_access_key_id> SECRET=<aws_secret_access_key> ENDPOINT=<lb ipaddress> VALIDATE_CERTS=<Tree/False> VERIFY_SSL=<True/False>

To install & configure specific tool(i.e aws):
make aws --makefile=scripts/s3_tools/Makefile ACCESS=<aws_access_key_id> SECRET=<aws_secret_access_key> ENDPOINT=<lb ipaddress> VALIDATE_CERTS=<Tree/False> VERIFY_SSL=<True/False>

To just configure specific tool(i.e. aws):
make aws-configure --makefile=scripts/s3_tools/Makefile ACCESS=<aws_access_key_id> SECRET=<aws_secret_access_key> ENDPOINT=<lb ipaddress> VALIDATE_CERTS=<Tree/False> VERIFY_SSL=<True/False>

To clean up all tools:
make clean --makefile=scripts/s3_tools/Makefile

```

## MongoDB as Configuration Management Database
Cortx-test uses MongoDB as backend to store Cortx setup details. These details, stored in MongoDB, are specific
to the setup itself. The purpose of this setup is to do automatic config generation
based on the setup. Not all values are mandatory and only applicable values needs to be filled in vm environment. A sample template is as shown below. This template is feed to database and pulled when developer will run test automation with test runner. The pulled templates merges with static yaml files to build the CMN_CFG and other component level configs.

```json

    {
    "setupname":"T2",
    "setup_in_useby": "",
    "in_use_for_parallel": false,
    "parallel_client_cnt": 0,
    "is_setup_free": true,
    "nodes":[
        {
            "host": "eos-node-0",
            "hostname": "node 0 hostname",
            "ip": "node 0 ip",
            "username": "node 0 username",
            "password": "node 0 password"
        },
        {
            "host": "eos-node-1",
            "hostname": "node 1 hostname",
            "ip": "node 1 ip address",
            "username": "node 1 username",
            "password": "node 1 password"
        }
    ],
    
    "enclosure":
    {
        "primary_enclosure_ip": "10.0.0.2",
        "secondary_enclosure_ip": "10.0.0.3",
        "enclosure_user": "",
        "enclosure_pwd": ""
    },
    
    "pdu":{
        "ip": "",
        "username": "",
        "password": "",
        "power_on": "on",
        "power_off": "off",
        "sleep_time": 120
    },
    
    "gem_controller":
    {
        "ip": "",
        "username": "",
        "password": "",
        "port1": "9012",
        "port2": "9014"
    },
    
    "bmc":
    {
        "username": "",
        "password": ""
    },
    
    "ldap":
    {
        "username": "",
        "password": "",
        "sspl_pass": ""
    },
    
    "csm":
    {
      "mgmt_vip": "",
      "csm_admin_user":{
        "username": "",
        "password": ""
      }
    
    },
    "s3":
    {
        "s3_server_ip": "",
        "s3_server_user": "",
        "s3_server_pwd": ""
    }
    }
```   
```
An example setup json configuration is shown below:
{"setupname": "RAS-Monitor",
"setup_type": "VM",
"setup_in_useby": "",
"in_use_for_parallel": false,
"parallel_client_cnt": 0,
"is_setup_free": true,
"nodes": [   {"host": "eosnode-1",
              "hostname": "ssc-vm-2793.colo.seagate.com",
              "ip": "10.230.248.51",
              "username": "root",
              "password": "",
              "public_data_ip": "192.168.61.218"},
             {"host": "eos-node-1",
             "hostname": "node 1 hostname",
             "ip": "node 1 ip address",
             "username": "node 1 username",
             "password": "node 1 password",
             "public_data_ip": "172.19.19.7"}
             ],
"enclosure": {"primary_enclosure_ip": "10.0.0.2",
              "secondary_enclosure_ip": "10.0.0.3",
              "enclosure_user": "manage",
              "enclosure_pwd": ""},
"pdu": {"ip": "",
      "username": "",
      "password": "",
      "power_on": "on",
      "power_off": "off",
      "sleep_time": 120},
"gem_controller": {"ip": "",
      "username": "",
      "password": "",
      "port1": "9012",
      "port2": "9014"},
"bmc": {"username": "",
       "password": ""},
"ldap": {"username": "sgiamadmin",
         "password": "",
         "sspl_pass": ""},
"csm": {"mgmt_vip": "ssc-vm-2793.colo.seagate.com",
        "csm_admin_user": {"username": "admin",
                            "password": ""}
                            },
"s3": {"s3_server_ip": "10.230.248.51", "s3_server_user": "root", "s3_server_pwd": ""}}
```

Script in project's path `tools/setup_update` can be used to generate a setup specific config entry. 
```commandline
python setup_entry.py --help
```
usage: setup_entry.py [-h] [--fpath FPATH] [--dbuser DBUSER]
                      [--dbpassword DBPASSWORD] [--new_entry NEW_ENTRY]
```

Update the setup entry

optional arguments:
  -h, --help            show this help message and exit
  --fpath FPATH         Path of the json entry file
  --dbuser DBUSER       Database user
  --dbpassword DBPASSWORD
                        database password
  --new_entry NEW_ENTRY
                        True for new entry , False for update

e.g. python3 tools/setup_update/setup_entry.py --dbuser <> --dbpassword <>

Name of setup specified in json file should be unique in case you are creating a new setup.
For example in sample json setupname value should be unique `"setupname":"T2"`.
```


## Steps to run test automation locally

### Run Cortx tests with test runner

If you want to anyway run the parallel tests sequentially. You should use --force_serial_run switch as shown in following command.
```commandline
python -u testrunner.py -te TEST-17412  -tp TEST-18382 --target s3-vm-2928 --force_serial_run True
```
If you want to run your test plan and test execution ticket with test runner, you should skip --force_serial_run switch.
```commandline
python -u testrunner.py -te TEST-17412  -tp TEST-18382 --target s3-vm-2928
``` 
When you want to run test and don't want to update Report DB or JIRA
```commandline
python -u testrunner.py -te TEST-17412  -tp TEST-18382 --target s3-vm-2928 --force_serial_run true --db_update False --jira_update False
```

 #### Test runner help
 
 >python -u testrunner.py --help
``` commandline
usage: testrunner.py [-h] [-j JSON_FILE] [-r HTML_REPORT] [-d DB_UPDATE]
                      [-u JIRA_UPDATE] [-te TE_TICKET] [-pe PARALLEL_EXE]
                      [-tp TEST_PLAN] [-b BUILD] [-t BUILD_TYPE] [-tg TARGET]
                      [-ll LOG_LEVEL] [-p PRC_CNT] [-f [FORCE_SERIAL_RUN]]
                      [-i DATA_INTEGRITY_CHK]
 
 optional arguments:
   -h, --help            show this help message and exit
   -j JSON_FILE, --json_file JSON_FILE
                         json file name
   -r HTML_REPORT, --html_report HTML_REPORT
                         html report name
   -d DB_UPDATE, --db_update DB_UPDATE
                         Update Reports DB. Can be false in case reports db is
                         down
   -u JIRA_UPDATE, --jira_update JIRA_UPDATE
                         Update Jira. Can be false in case Jira is down
   -te TE_TICKET, --te_ticket TE_TICKET
                         jira xray test execution id
   -pe PARALLEL_EXE, --parallel_exe PARALLEL_EXE
                         parallel_exe: True for parallel, False for sequential
   -tp TEST_PLAN, --test_plan TEST_PLAN
                         jira xray test plan id
   -b BUILD, --build BUILD
                         Build number
   -t BUILD_TYPE, --build_type BUILD_TYPE
                         Build type (Release/Dev)
   -tg TARGET, --target TARGET
                         Target setup details
   -ll LOG_LEVEL, --log_level LOG_LEVEL
                         log level value
   -p PRC_CNT, --prc_cnt PRC_CNT
                         number of parallel processes
   -f [FORCE_SERIAL_RUN], --force_serial_run [FORCE_SERIAL_RUN]
                         Force sequential run if you face problems with
                         parallel run
   -i DATA_INTEGRITY_CHK, --data_integrity_chk DATA_INTEGRITY_CHK
                         Helps set DI check enabled so that tests perform
                         additional checksum check
   -pf PRODUCT_FAMILY, --product_family
                        Helps to select product family type whether LR or local
   -c  VALIDATE_CERTS, --validate_certs
                        This gives option whetherValidate HTTPS/SSL certificate 
                        to S3 endpoint needs to be validated or not.
   -s USE_SSL,  --use_ssl
                     Option whether HTTPS/SSL connection for S3 endpoint should be used or not.
   -hc HEALTH_CHECK --health_check
                     Decide whether to do health check (on server) or not with tests execution.
  ```
#### Running Test locally in distributed mode
```commandline
pytest --local=True -d --tx 3*popen -rA unittests\Your_Test_Module.py
```
```properties
3 is number of worker processes to be spawned.
```
#### Running test plans in dev environment
##### With dist mode
```commandline
pytest --capture=no --te_tkt TEST-17412 -d --tx 2*popen -rA unittests\Your_Test_Module.py

```
##### With sequential execution
```commandline
pytest --capture=no --te_tkt TEST-17412 -rA unittests\test_reporting_and_logging_hooks.py
```

## Client Hardware Configuration
While ordering client on ssc-cloud, make sure
    1. Have at least 8GB RAM for it, to support 1GB object size in s3bench tests.
    2. For more large number of parallel IO connections, good to have 8 CPUs.
    3. Default 1GB of swap space is provided, need to order 1 extra disk, and create swap space out of extra disk, and mount it.
        Procedure to create swap space of 8 GB: [A gist from one of the articles](https://www.thegeekdiary.com/centos-rhel-how-to-add-new-swap-partition/)
        * Create new partition using fdisk command
            * `fdisk /dev/sdb` # sda will generally have OS installation
            * new (option `n`), primary (option `p`) partition, Default partition number, Default first sector, Last Sector `+8G`, Write (option `w`)
        * Create swap on the partition using `mkswap /dev/sdb1` # Provide above created partition number i.e. sdb1
        * Mount swap using `swapon /dev/sdb1`

    ## Increase client root space size should be at least 50 GB using following commands
    Please utilize free disks from the output of lsblk
    Note: In case of multipart/Big object upload, disk space requirement may change/increase.
    resize2fs is specific to ext2/3/4. In case /root is formatted with xfs we need to use the xfs_growfs tool 
    e.g. "xfs_growfs /dev/mapper/vg_sysvol-lv_root"
    We can run lvextend as "lvextend /dev/mapper/vg_sysvol-lv_root -l +100%FREE" to consume all the free PE
    ```
    df -h
    lsblk 
    pvcreate /dev/sdb
    vgextend vg_sysvol /dev/sdb
    lvextend /dev/mapper/vg_sysvol-lv_root -L +50G
    resize2fs /dev/mapper/vg_sysvol-lv_root
    df -h
    ```

    ## increase the swap space, Please utilize free disks from the output of lsblk
    ```
    lsblk 
    pvcreate /dev/sdi
    vgextend vg_sysvol /dev/sdi
    lvextend /dev/mapper/vg_sysvol-lv_swap -l +100%FREE
    swapoff /dev/mapper/vg_sysvol-lv_swap
    mkswap /dev/mapper/vg_sysvol-lv_swap
    swapon /dev/mapper/vg_sysvol-lv_swap
    ```


