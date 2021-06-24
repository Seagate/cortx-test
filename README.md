# cortx-test
Test Automation project for LDR R2 and future versions.

## Set up dev environment
    
    1. `yum update -y`
    
    2. `yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make sqlite-devel`
    
    3. `cd /usr/src && wget https://www.python.org/ftp/python/3.7.9/Python-3.7.9.tgz && tar xzf Python-3.7.9.tgz && rm Python-3.7.9.tgz`
    
    4. `cd /usr/src/Python-3.7.9 && ./configure --prefix=/usr --enable-optimizations`
    
    5. `cd /usr/src/Python-3.7.9 && make altinstall`
    
    6. Create a softlink to point to this installation. You can check the folder created and 
    improvise following command.
       `ln -s /usr/local/bin/python3.7 python3.7
    
    7. `yum install -y python3-devel librdkafka nfs-utils python3-tkinter`
    
    8. `python3.7 -m venv virenv`
    
    9. `source virenv/bin/activate` or use old style `. ./virenv/bin/activate`
      
    8. `pip install --upgrade pip`
    
    9. `pip install pysqlite3`
    
    10. `pip install --ignore-installed -r requirements.txt`
    
    11. Install awscli with default python 3.6 pre installed with inhouse vm images and 
    configure aws and copy cert file.
    
    Alternatively by skipping step 8 to 10, you can also set python environment with using virtual env.

## MongoDB as Configuration Management Database
Cortx-test uses MongoDB as backend to store Cortx setup details. These details are specific
to the setup itself. The purpose of this setup is to do automatic config generation
based on the setup. A sample template is as shown below.

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

Script in project's path `tools/setup_update` can be used to generate a setup specific config entry. 
```commandline
python setup_entry.py --help
usage: setup_entry.py [-h] [--fpath FPATH] [--dbuser DBUSER]
                      [--dbpassword DBPASSWORD] [--new_entry NEW_ENTRY]

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

## Steps to setup s3 client
Script in project's path `scripts/s3_tools/Makefile` can be used to install s3 tools on client.
```commandline
Required arguments:
    ACCESS=<aws_access_key_id>
    SECRET=<aws_secret_access_key>
optional arguments:
    -i, --ignore-errors  Ignore all errors in commands executed to remake files.
    -k, --keep-going     Continue as much as possible after an error.
    ENDPOINT=<s3_endpoint>
    CA_CRT=<certificate_file_path>
    NFS_SHARE=<NFS_share_jclient_path>

cd scripts/s3_tools/
make help
    install-tools: Install tools like aws, s3fs, s3cmd, minio, call in case its a new machine.
    aws          : Install & configure aws tool.
    s3fs         : Install & configure s3fs tool.
    s3cmd        : Install & configure s3cmd tool.
    jcloud-client: Setup jcloud-jclient.
    minio        : Install & configure minio tools. credentials: Eg make minio ACCESS=<new-accesskey> SECRET=<new-secretkey>

To install & configure all tools:
make clean # Perform cleanup.
make install-tools ACCESS=<aws_access_key_id> SECRET=<aws_secret_access_key>

To install & configure specific tool(i.e aws):
make aws ACCESS=<aws_access_key_id> SECRET=<aws_secret_access_key>

To cleanup all tools:
make clean

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
  ```
#### Running Test locally in distributed mode
```commandline
pytest --local=True -d --tx 3*popen -rA unittests\<Your_Test_Module>.py
```
```properties
3 is # of worker processes to be spawned.
```
#### Running test plans in dev environment
##### With dist mode
```commandline
pytest --capture=no --te_tkt TEST-17412 -d --tx 2*popen -rA unittests\<Your_Test_Module>.py

```
##### With sequential execution
```commandline
pytest --capture=no --te_tkt TEST-17412 -rA unittests\test_reporting_and_logging_hooks.py
```

## How to automate component level test cases
Components level tests can be either pure component level tests which run 
1. Tests run in the same process as code to be tested 
2. Tests run in another process and interact with the component over a protocol (RPC/HTTP)  
3. Test runs in another process where component is available as a service and where cortx-test and it's capabilities can be used. 

Some of the setup steps like "MongoDB as Configuration Management Database" should not be required for component level tests. 

* In case 1) Component tests can be automated as a seperate mini framework utilizing cortx-test or have their own libraries. This can then be integrated with test execution and reporting framework.
* In case 2) Component tests can utilize cortx-test directly and build their own libraries to test components.
* In case 3) Component tests can be written in cortx-test and utilize all the capabilities of the framework.

