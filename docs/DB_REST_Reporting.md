# REST-DB & Reporting Framework

<img src="media\rest_server.png" style="width:5.02084in;height:3.96875in" />

# Entities

1.  **Test Execution Framework:** Cortx test automation framework used for executing all automated QA tests.

2.  **User:** Any person who is using test execution framework or reporting web page.

3.  **Reporting web page:** Web page for showing QA execution reports. It will fetch data from MongoDB to show data on webpage.

4.  **REST Server:** It is flask-based rest server. It will provide REST apis for all database operations.

5.  **Dash Reporting Server:** Dash is a productive Python framework for building web analytic applications. Written on top of Flask.

6.  **Mongo DB:** MongoDB is an open-source document database and leading NoSQL database. It will be used for storing all test execution data.

7.  **REST APIs:** A RESTful API is an architectural style for an application program interface (API) that uses HTTP requests to access and use data. That data can be used to GET, PUT, POST and DELETE data types, which refers to the reading, updating, creating and deleting of operations concerning resources. Here, REST APIs will be used for all DB related operations.

8.  **PyMongo:** PyMongo is a Python distribution containing tools for working with MongoDB and is the recommended way to work with MongoDB from Python. REST APIs internally will use pymango for accessing mango DB.

9.  **IC2 Server Machine:** IC2 (cftic2.pun.seagate.com) is physical server machine in pune lab. MongoDB is hosted on this machine.

# Flow

1.  User will start test execution using test execution framework.

2.  Test execution framework will run tests on LR cluster. After test execution, it will collect some test specific data.

3.  Test execution framework will store test specific data in mongo DB using REST API provided by REST server.

4.  User will access reporting web page to get test execution reports. Based on user inputs on web page, web page back end code (dash reporting server code) will fetch data from mongo DB using REST APIs.

5.  Fetched data will be post processed and showed to user on web page.

# Database Schema

Mongo DB Collection for storing test execution details.

| **Field Name**                                | **Mandatory** | **Index** |
|-----------------------------------------------|---------------|-----------|
| **Setup details:**                            |               |           |
| Client Machine hostname                       | Y             |           |
| Number of nodes                               | Y             |           |
| OS (Centos version for Node)                  | Y             |           |
| Node hostname (For each node)                 | Y             |           |
| **Test details:**                             |               |           |
| Test Name                                     | Y             |           |
| Test id                                       | Y             |           |
| Test id labels                                | Y             |           |
| Test tag if any                               | Y             | Y         |
| Test plan id                                  | Y             | Y         |
| Test execution id                             | Y             | Y         |
| Test type: Avocado/CFT/Locust/S3bench/ Pytest | Y             |           |
| Test Component: S3, CSM, Motr etc.            | Y             |           |
| Test team: CFT / Automation / Component test  | Y             |           |
| Test Start time                               | Y             |           |
| Test Execution time                           | Y             |           |
| Build type: Release/beta                      | Y             |           |
| Build No                                      | Y             | Y         |
| Log path                                      | Y             |           |
| Test result                                   | Y             | Y         |
| Health Check Post Test: Pass/Fail             | Y             |           |
| Automated/Manual                              | Y             |           |
| **In case of failure:**                       |               |           |
| Issue Type: Dev/Test issue                    |               |           |
| Issue id: bug id                              |               |           |
| Is regression: Known issue                    |               |           |
| Log collection done: true/false               |               |           |
| **Timing Details:**                           |               |           |
| Node Reboot Time                              |               |           |
| All Service Start Time                        |               |           |
| All Service Stop Time                         |               |           |
| Bucket Deletion Time                          |               |           |
| Bucket Creation Time                          |               |           |
| Boxing Time                                   |               |           |
| Unboxing Time                                 |               |           |
| Update Time                                   |               |           |
| Deployment Time                               |               |           |

# Authentication for REST server 

Will be implemented using the database login credentials

-   Authentication will only be implemented for POST/PATCH request

-   Authentication will not be implemented for GET method

-   For POST/PATCH request, username/password should be passed as part of body of request

We already have users created in database username: datawrite, dataread. And authentication will be done using those only.

# REST Server Endpoints

1.  Login

    1.  GET

2.  TestID

    1.  GET - Get results by Test ID

    2.  POST - Create new Entry

    3.  PATCH - Modify existing entry

3.  Build

    1.  GET - Get results by build

4.  TestExecutionID

    1.  GET - Get results by TestExecutionID

5.  TestPlanID

    1.  GET - Get results by TestPlanID

6.  TestTeam

    1.  GET - Get results by TestTeam

7.  Search

    1.  GET – Search results, can be used for mixed query

# API Status Response

| **Code** | **Description**                                                                                                                                                                            |
|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 200      | OK: successful.                                                                                                                                                                            |
| 400      | Bad Request: Request body is missing, or Username or password is missing                                                                                                                   |
| 401      | No Data Found                                                                                                                                                                              |
| 422      | Unprocessable Entity: server understands the content type of the request entity, and the syntax of the request entity is correct, but it was unable to process the contained instructions. |
| 499      | Call Cancelled: Call cancelled by client.                                                                                                                                                  |
| 500      | Internal Server Error: When requested resource is not available.                                                                                                                           |

# Reporting Webpage

**URL (LR R1: http://cftic2.pun.seagate.com:5002/)**

User will use reporting webpage to generate build wise reports.

**Features:**

+ Generate build wise reports

+ Provide interface to read data from mongo DB

+ Generate PDF/Word format report file
