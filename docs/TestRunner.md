# Test Runner

<img src="media\test_runner.png" style="width:5.02084in;height:3.96875in" />

## Flow

1.  Test runner will receive json input from kafka.

2.  Input json structure:

    +   timestamp:
    +   test_name:
    +   filename:
    +   tag:
    +   kafka id:
    +   other_db_params

3.  User can provide test name/filename/tag for tests to execute. If more than one field is provided then priority sequence will be,

    1.  Test_name
    2.  Filename
    3.  Tag

    e.g., If user provides tag and test_name in json, then runner will run only test with test_name provided.

4.  Based on input json, runner will trigger test execution.

5.  After test execution completes, runner will capture required test execution details e.g., test status etc.

6.  Using DB REST API, Runner will update mongo DB with test execution details from log file and parameters received in input json file.

    other_db_params expected in json are,

    +   Test Name
    +   Test id
    +   Test id labels 
    +   Test tag if any 
    +   Test plan id
    +   Test execution id 
    +   Test type: Avocado/CFT/Locust/S3bench/ Pytest 
    +   Test Component: S3, CSM, Motr etc. 
    +   Test team: CFT / Automation / Component test 
    +   Build type: Release/beta 
    +   Build No 
    +   Test result

7.  Runner will send response to kafka saying that test execution is done for given kafka id.
