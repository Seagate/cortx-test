
## Why moving from CTP and Avocado based test framework
CTP OS and Avocado based test framework was used to develop automated test cases in Cortx R1/MVP. It had a binding to CentOS image which has Avocado and helper RPMs pre-installed for automation. Tests were written and run assuming prerequisites Python packages were installed. There was a hard dependency on CTP OS clients to run test automation. This framework was primarily aimed at testing firmware products and not for private cloud based solutions. It lacked parallel and distributed test execution capabilities.

# Use of Python
  Decision to continue with Python was based on team's expertise, speed of development and multi programming paradigms like OO and functional programming. Developers can use suitable programming style and associate language constructs and capabilities for a given job.  
  
# Use of Pytest
Pytest framework has lot to offer in terms of testing at system or integration level. It's easier to write small test, yet scales to support more complex integration and system level tests. It was evaluated for all test framework requirement with small tests and some of which are mentioned below.
* Supports parallel execution
* Supports tagging 
* modular fixtures for short and long lived resources
* Plugin architecture and 300+ community supported plugins

# High level repository structure
The Cortx-test automation project's code can borken into 3 loosely coupled parts 
* Test automation framework  
* Distributed test execution framework ./core ./execution
* Reporting framework   ./reporting_service

## Repository structure
Overview of folder structure in cortx-test repository.

## commons
### `helpers`
Provides various helpers related to node operations, bmc , s3 , nfs , etc. 
### `utils`
Utilities for different purposes and concerns. Utility names are intuitive and they don't save any state. Ideally generic functions or static methods.
### `conftest`
common fixtures used in test framework.
### `exceptions`
Exception classes and error codes. 

## config
Common config and all other component specific config. Test suite and test specific configs would be minimalistic and test and test suite fixtures should test data creation and distruction.

## core
For test execution framework codebase, hooks and common libraries.

## libs
All test libraries code should go here and should be grouped by product component or features.

## tests
Test universe

## reporting_service
Its a REST service which provides APIs to stores build wise test results and aggregate stats and query capabilities. 
```
├───ci_tools
│       .pylintrc
│       requirements-pip.txt
│       scripts
├───commons
│   │   conftest.py
│   │   errorcodes.py
│   │   exceptions.py
│   │   Globals.py
│   │   __init__.py
│   │
│   ├───helpers
│   │       bmc_helper.py
│   │       node_helper.py
│   │       salt_helper.py
│   │       s3_helper.py
│   │       csm_cli_helper.py
│   │       *_helper.py
│   │
│   ├───utils
│   │       assert_utils.py
│   │       db_utils.py
│   │       infra_utils.py
│   │       json_utils.py
│   │       yaml_utils.py
│   │       worker_pool.py
│   │       *_utils.py        
│   
│
├───config
│       common_config.yaml
│       csm_config.yaml
│       di_config.yaml
│       constants.py
│       params.py
│       __init__.py
│
├───core
│   │   kafka_*.py
│   │   discover_test.py
│   │   execution_plan.py
│   │   _top_runner.py
│   │   reporting_connector.py
│   │   distributed_runner.py
│
├───libs
│   └───di
│           di_destructive_step.py
│           di_lib.py
│           di_mgmt_ops.py
│           di_params.py
│           di_test_framework.py
│
├───tests
│   └───di
│           test_di.py
│
├───reporting_service
│   │
│   │  report_api.py
│   │  report_bl.py
│   │  report_dl.py
│   │  mongodb_adapter.py  
│
├───unittests
│   │   test_ordering.py
│   │   test_pytest_features.py
│   │
│
└───logs
	│   pytestfeatures.log
    │   report.html
		testdir
		│   *test_result_dir_for_executed_test*
			│  testcase.log

```

# Hardware Configuration for test automation setup
VMs or Physical machines with 16-32 GB RAM and 8-16 logical cores would be a decent configuration for a test machine. The deployment view of HLD discusses more about the deployment structure. The least requirement is that there should be a connectivity to the Cortx setup in labs.



