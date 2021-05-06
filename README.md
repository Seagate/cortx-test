# cortx-test
Test Automation project for LDR R2 and future versions.

## Set up dev environment:

1. `yum update -y`
2. `yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make sqlite-devel`
3. `cd /usr/src && wget https://www.python.org/ftp/python/3.7.9/Python-3.7.9.tgz && tar xzf Python-3.7.9.tgz && rm Python-3.7.9.tgz`
4. `cd /usr/src/Python-3.7.9 && ./configure --prefix=/usr --enable-optimizations`
5. `cd /usr/src/Python-3.7.9 && make altinstall`
6. Create a softlink to point to this installation.
7. `yum install -y python3-devel librdkafka nfs-utils python3-tkinter`
8. `python3.7 -m venv virenv`
9. `source virenv/bin/activate` or use old style `. ./virenv/bin/activate`  
8. `pip install --upgrade pip`
9. `pip install pysqlite3`
10. `pip install --ignore-installed -r requirements.txt`
11. Install awscli with default python 3.6 pre installed with inhouse vm images and 
configure aws and copy cert file.

Alternatively by skipping step 8 to 10, you can also set python environment with using virtual env.

## Steps to run test automation locally:

### Run cortx tests with test runner.

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
#### Running Test locally in distributed mode:
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


