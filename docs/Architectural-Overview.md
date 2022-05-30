## Introduction

cortx-test repository hosts a test automation framework called Gliese. It has test runner entities called corbots. In
distributed mode all corbots assume responsibility of work horses and primebot works as a producer who plans test
execution strategy and distribute the work among multiple corbots. The framework supports testing in parallel within
corbot context and intend to optimize execution time by conducting tests with multiple CORTX setups.

## Background

For QA certification of an enterprise product, it is always a challenge to execute the test universe within a finite
timeframe (typically a day) especially since the test universe has thousands of test cases of several types including
component, system, and performance tests. Job schedulers and CI tools like Jenkins solve this problem to an extent by
providing functionality to executing multiple tests on different machines, however it is always hard to monitor numerous
test executions and deploy and manage targets and complete certification of a build within a day. The algorithms and
methods mentioned in the paper explain design and implementation of test executor framework which solves this problem
with automatic test configuration management, parallel test execution, reporting and storage efficiency.

## Why move from CTP and Avocado based test framework

CTP OS and Avocado based test framework was used to develop automated test cases in CORTX R1/MVP. It had a binding to
CentOS image which has Avocado and helper RPMs pre-installed for automation. Tests were written and run assuming
prerequisites Python packages were installed. There was a hard dependency on CTP OS clients to run test automation. This
framework was primarily aimed at testing firmware products and not for private cloud based solutions. It lacked parallel
and distributed test execution capabilities at that point in time.

## Use of Python

Decision to continue with Python was based on team's expertise, speed of development and multi programming paradigms
like OO and functional programming. Developers can use suitable programming style and associate language constructs and
capabilities for a given job.

## Use of Pytest

Pytest framework has lot to offer in terms of testing at system or integration level. It's easier to write small test,
yet scales to support more complex integration and system level tests. It was evaluated for all test framework
requirement with small tests and some of which are mentioned below
*   Supports parallel execution
*   Supports tagging
*   Modular fixtures for short and long-lived resources
*   Plugin architecture and 300+ community supported plugins

## High level repository structure

The Cortx-test automation project's code can logically divided into 3 loosely coupled parts

*   Test automation framework
*   Distributed test execution framework ./core ./execution
*   Reporting framework ./reporting_service

### Repository structure

Overview of folder structure in cortx-test repository.

### commons

Cosists of helpers and utils.

#### `helpers`

Provides various helpers related to node operations, bmc , s3 , nfs , etc.

#### `utils`

Utilities for different purposes and concerns. Utility names are intuitive and they don't save any state. Ideally
generic functions or static methods.

#### `exceptions`

Exception classes and error codes.

### config

Common config and all other component specific config. Test suite and test specific configs would be minimalistic and
test and test suite fixtures should test data creation and distruction.

### core

For test execution framework codebase, hooks and common libraries.

### libs

All test libraries code should go here and should be grouped by product component or features. Test libraries uses core
libraries and utilities to achieve test actions. Test libraries are reused by multiple test modules.

### tests

Part of Test Universe comprising system and end to end tests. All tests are grouped by high level product component and
capabilities. e.g. S3, HA, Durability, etc.

### comptests

Comprises component level black box tests. All tests are grouped by high level product components like Motr, HA,
Provisioner, etc.

### `conftest`

common fixtures used in test framework.

### reporting_service

Its a REST service which provides APIs to stores build wise test results and aggregate stats and query capabilities.

Here is the diagrammatic representation:

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

## Hardware Configuration for test automation setup

VMs or Physical machines with Linux flavor having 16-32 GB RAM and 8-16 logical cores would be a decent configuration
for a test machine. Minimal test machine configuration is 4 GB RAM and 2 logical cores which is suitable for development
environment. The deployment view [Test Execution Deployment](Test-Execution-Deployment-View.md) discusses more about the
deployment structure. The least requirement is that there should be a network connectivity of these client VMs i.e Cloud
Form Vms, virtualization platform VMs or physical machines to the Cortx setups in labs or public cloud services like AWS
EC2.

### Abbreviations and Definitions

*   Target: A target is an application deployment under test

*   Corbot: A program which sets up necessary environment and pre-requisites to run test automation pointing to a single
  target

*   Test Execution Framework: Loosely coupled test framework module responsible for collecting test metadata from Jira and
  executing optimized execution ticket provided by Kafka

*   Test Executor framework: Same as a test execution framework

*   Dist Runner: Test execution framework module loosely coupled for test framework and consumer module of execution
  framework. It is responsible for collecting test metadata from Jira and creating an optimized test execution plan as
  per Jira Test Plans

*   Chaos and destructive testing framework: A sub framework responsible for implementing libraries to generate
  destructive test scenarios and chaos in Target deployments

*   Object Store Data Integrity framework: A sub framework which stores s3 client state and provides library to test
  versioned object Store data integrity interleaved across object store version upgrade and after object store downtime

*   HA Tests: High availability test cases which test Consistency, Availability and Reliability of Object Store

*   Test Client: A separate VM or Container configured with Python Environment and prerequisites Linux and Python site
  packages to run automated test cases

### Framework Components

The following diagram shows all components/modules present in framework.

*   Primebot: This module reads test execution data from test management tool. From this test execution data, it
  identifies which tests need to be executed. It performs analytics on test data and divides test cases into different
  chunks. Those chunks are executed by individual execution Corbot.

*   Distributed Kafka: This is the communication channel between Primebot and execution Corbot. Multiple approaches like
  RPC based mechanism like XML RPC and Zero MQ were evaluated for test distribution mechanisms. Kafka provides a
  producer and multi consumer model which fits in our context.

*   Execution Corbot: It reads the test data from Kafka channel and using that data it schedules the test execution.

*   Dashboard: Dashboard is a web page where all test data is available to users. Dashboard gets all data from mongo dB
  using dB rest interface. DB rest interface is designed to provide access of mongo dB to different components in
  framework.

*   Test Management Interface: This is designed to interact with any test management tool. In this framework, this
  framework interacts with JIRA X-ray test management tool, it does CRUD operation on test management tool.

*   Logging: Logging support is provided by framework. It captures all the required logs. After test executions, framework
  stores all logs to nfs share, so that it can be accessible to user at any time.

*   Health Check: This module checks the health of target system. If the target system is in bad condition, then there is
  no use of using that system for test execution. So, before starting any test, framework checks the health of the
  target system using this module. If the system is not healthy, then framework schedules the test execution on another
  healthy system.

*   Config Management: All the test data which is required for test execution is managed by this module. Target specific
  config data is stored in MongoDB, test suite specific config data is stored in Jira/database, and test specific data
  is stored locally. This module captures and aggregates config data and makes that data/config maps available to all
  tests during execution.

### Target Locking

Below diagram explains the flow of target locking mechanisms. This mechanism provides two types of locks: Shared and
exclusive. If the request is for parallel test execution, then it will search for systems with shared lock, as existing
system with parallel execution can be used to schedule additional parallel tests. If the request is for sequential test
execution, then it will search for a system with exclusive lock, which will be dedicated system for that execution.

For any parallel test execution request, priority will be system with shared lock. If such a system is not available,
then it will check availability of system with exclusive lock. This module allocates the system only if that system is
healthy.

### Framework Deployment Flow

This framework can be deployed and used in two ways. In multi Corbot setup mode and single Corbot setup mode.

### Multi Corbot's setup

sequence 1 to 6 is explained below in points.

Jenkins/Scheduler triggers a job which supplies parameters like targets and config to distributed executor i.e. Primebot

Primebot runs in distributed mode and creates an execution plan which determines the sequence of test execution and
which tests can be run in parallel. This execution plan's entries are fed to Kafka topic cortx-test-jobs in JSON format.

Test runners (single Corbot) are running in distributed mode on one or more virtual machines which have Kafka consumer.
They belong to the same consumer group, and it is guaranteed that a test will be executed only once by any of the test
runners.

The deserialized JSON is parsed, and test metadata is sent to Corbots (using pytest runner) to run either test with a
parallel tag in parallel or other tests in serial order. Corbot also decides the target (Setup) to run tests against it
from parsed JSON.

Multiple Corbots can point to the same target. Optimal utilization of target is decided on tags or markers attached to a
test function. e.g., marker with non-destructive tag can run in parallel across Corbots deployed on different virtual
machines/ containers. Target Locking section in Framework components explains about how target is utilized for efficient
test execution.

Test reporting data is saved by Restful Reporting Server to Mongo DB through Reporting client API. Reporting Client is
called at the end of pytest test run with pytest reporting hook. This data is retrieved from Reporting server for
further analytics and presentation.

## Single corbot's setup

This setup is useful when there is only one target. It is designed to be used by developers for their test
validation/development. This setup uses a single corbot.

## Framework at system level

Below diagram shows how this framework resides in any system and shows it’s use cases to different applications.

### Benefits

*   Can run on commodity H/W and light weight VMs. The run can be started on a single client VM for multiple targets (
  Storage efficient)

*   Framework will start parallel execution on multiple targets; depending on health of target, it will reschedule test
  execution for errored or failed tests. This will ensure complete test execution of identified test plan

*   Framework will have parallel execution over a single target also which will reduce the time required for test
  execution (Time efficient)

*   Maximum failures will get during the first few hours of execution

*   Live test execution information will be available to users through dashboard and test management tool

*   Complete history of test data will be available in database, so anyone can access any test related data at any time
  from dashboard.

*   Logs will be archived on NFS share

*   No manual intervention is required for test configuration of different targets as the process is fully automated
