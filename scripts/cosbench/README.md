###### **EOS COSBENCH AUTOMATION**


**About Cosbench:**
CosBench is a distributed benchmark tool to test cloud object storage systems.
COSbench consists of two key components: 
* Driver (also referred to as COSBench Driver or Load Generator).
* Controller (also referred to as COSBench Controller).
-Driver is responsible for workload generation, issuing operations to target cloud object storage, and collecting performance statistics.
 Can be accessed via http://<driver-host>:18088/driver/index.html.
-Responsible for coordinating drivers to collectively execute a workload, collecting and aggregating runtime status or benchmark results from driver instances, and accepting workload submissions.
 Can be accessed via http://<controller-host>:19088/controller/index.html.
-The controller and driver can be deployed on the same node or different nodes,and the                node can be a physical machine or virtual machine (VM) instance.
-Cosbench user guide - one can reffer to the following intel 
git link: https://github.com/intel-cloud/cosbench/blob/master/COSBenchUserGuide.pdf


**Cosbench Automation Scripts used for:**
1. Install/Configure cosbench on controller node and driver nodes.
2. Execution of Workload.
3. Analysis of reports generated(csv,Html and graph)


**Cosbench Prerequistes:**
- You need a client VM/machine wih EOS which can connect to Mero S3 server. 
- Cosbench Setup(Minimum one vm) and S3Server setup.

**Configure client using below steps:**
Python Prerequisite installation:
1.  One Controller and one Driver can be installed on single VM for more drivers user needs to have more VM.
3. On the controller VM user needs to install python pre-requisites using start_setup.sh.
4. Following setup file is available under following path eos-test/utils/setup_client/start_setup.sh
5. User need to update the config file before running the start_setup.sh script.


**Scripts/Useful Config ini file Info:**
- start_setup.sh : This script is located under /root/eos-test/utils/setup_client/. This script takes care of all  prerequistes required for cosbench automation on cosbench controller nodes.
- Config.ini : This file is located under /root/eos-test/utils/setup_client,in this file we need to mention S3 server IP address and its login credentials.


Cosbench Config .ini : This file is located under /root/eos-test/utils/cosbench.
In this file we need to specify cosbench driver nodes details and access key and secret key details. Here we have S3 endpoint details as well.
Also we can specify below workload properties and its value which would be used during script run:
[WORKLOADPROPS]
no_of_buckets=2 ( Number of buckets that will be created)
no_of_objects=6 ( Number of objects that will be created)
object_size_in_mb=1 (Object Size in MB)
run_time_in_seconds=100 (Runtime in secs)


Cosbench_performance.py :  This is the main script which take care of performance execution in three workload types modes : Read,write and Mixed and below options mentioned. 
usage: cosbench_performance.py [-h] [--install] -w WORKERS --buildver BUILDVER
                               [-b BUCKETS] [-o OBJECTS] [-os OBJSIZE]
                               [-r RUNTIME] [-ak ACCESSKEY] [-sk SECRETKEY]
                               [-ep ENDPOINT] [-t WORKLOADTYPE]


**Getting Started:**
```1. Download Project Repository :
git clone https://seagit.okla.seagate.com/eos/qa/eos-test.git
2. git checkout Dev 
3. Once done step 1 and 2 , will have eos-test directory under /root
4. Go to setup_client folder under /root/eos-test,configure the config.ini file
  and run start_setup.sh.
5. Activate the virtual environement.
source <path-to-'eos-test'>/eos-test/venv/bin/activate
6. Navigate to /root/eos-test/utils/cosbench folder and configure the config.ini file.
7. Then execute the python cosbench_performance.py file.
8. Post successfull run we would have "COS" directory created under /root which contains all cosbench binaries and installables.
```

Post run logs/Result Verification:
- Results are captured in CSV,HTML and Graph Format.
- Both csv and html files are located under /root/eos-test/utils/cosbench folder.