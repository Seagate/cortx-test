# REST server APIs guide
### While consuming any API:
1. Include `Content-Type: application/json` in request headers
2. Include `username` and `password` in json body
## Endpoints
### 1. create
* Can be used to create new execution entries in database
* Data types for database fields

    | Mandatory | Field Name | Data Type |
    | --- | ---------- | --------- |
    | Yes | clientHostname | String |
    | Yes | noOfNodes | Integer |
    | Yes | OSVersion | String |
    | Yes | nodesHostname | List of String |
    | Yes | testName | String |
    | Yes | testID | String |
    | Yes | testIDLabels | List of String |
    | Yes | testTags | List of String |
    | Yes | testPlanID | String |
    | Yes | testExecutionID | String |
    | Yes | testType | String |
    | Yes | testComponent | String |
    | Yes | testTeam | String |
    | Yes | testStartTime | String in ISO 8601 |
    | Yes | testExecutionTime | Integer |
    | Yes | buildType | String |
    | Yes | buildNo | String |
    | Yes | logPath | String |
    | Yes | testResult | String |
    | Yes | healthCheckResult | String |
    | Yes | executionType | String |
    | No | issueType | String |
    | No | issueID | String |
    | No | isRegression | Boolean |
    | No | logCollectionDone | Boolean |

#### Examples:
1. Command line
```
curl -L -X POST 'http://127.0.0.1:5000/create' \
-H 'Content-Type: application/json' \
--data-raw '{
    "OSVersion": "CentOS",
    "buildNo": "0002",
    "buildType": "Release",
    "clientHostname": "iu10-r18.pun.seagate.com",
    "executionType": "Automated",
    "healthCheckResult": "Fail",
    "isRegression": false,
    "issueID": "EOS-000",
    "issueType": "Dev",
    "logCollectionDone": true,
    "logPath": "DemoPath",
    "noOfNodes": 2,
    "nodesHostname": [
        "sm7-r18.pun.seagate.com",
        "sm8-r18.pun.seagate.com"
    ],
    "testComponent": "S3",
    "testExecutionID": "TEST-0000",
    "testExecutionTime": 0,
    "testID": "TEST-0000",
    "testIDLabels": [
        "Demo",
        "Labels"
    ],
    "testName": "Demo test",
    "testPlanID": "TEST-0000",
    "testResult": "Pass",
    "testStartTime": "2020-12-29T09:01:38+00:00",
    "testTags": [
        "Demo",
        "Tags"
    ],
    "testTeam": "CFT",
    "testType": "Pytest",
    "username": "username",
    "password": "password"
}'
```
2. python - requests
```
import requests
import json
endpoint = create
host = "http://127.0.0.1:5000/"

payload = {
    "OSVersion": "Redhat",
    "buildNo": "0000",
    "buildType": "Release",
    "clientHostname": "iu10-r18.pun.seagate.com",
    "executionType": "Automated",
    "healthCheckResult": "Fail",
    "isRegression": false,
    "issueID": "EOS-000",
    "issueType": "Dev",
    "logCollectionDone": true,
    "logPath": "DemoPath",
    "noOfNodes": 2,
    "nodesHostname": [
        "sm7-r18.pun.seagate.com",
        "sm8-r18.pun.seagate.com"
    ],
    "testComponent": "S3",
    "testExecutionID": "TEST-0000",
    "testExecutionTime": 0,
    "testID": "TEST-1111",
    "testIDLabels": [
        "Demo",
        "Labels"
    ],
    "testName": "Demo test",
    "testPlanID": "TEST-0000",
    "testResult": "Pass",
    "testStartTime": "2020-12-29T09:01:38+00:00",
    "testTags": [
        "Demo",
        "Tags"
    ],
    "testTeam": "CFT",
    "testType": "Pytest",
    "username": "username",
    "password": "password"
}
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("POST", host+endpoint,
                            headers=headers, data=json.dumps(payload))

print(response.text)
```

#### HTTP Status Code:
|Code | Description |
|-----|-------|
|200 | Success |
|400 | Bad Request: Missing parameters. Do not retry. |
|401 | Unauthorized: Wrong username/password. |
|403 | Forbidden: User does not have permission for operation. |
|503 | Service Unavailable: Unable to connect to mongoDB. |

### 2. search
* Can be used to search previous execution entries in database
* Can pass the exact query which can be executed using 
[db.collection.find](https://docs.mongodb.com/manual/reference/method/db.collection.find/#db.collection.find).
This allows to execute complex queries using operators.

#### Examples:
1. Command line
```
curl -L -X GET 'http://127.0.0.1:5000/search' \
-H 'Content-Type: application/json' \
--data-raw '{
    "buildNo": "531",
    "testID": "TEST-10",
    "healthCheckResult": "Fail",
    "testComponent": { "$in": ["S3", "Motr", "CSM"] },
    "username": "username",
    "password": "password"
}'
```
2. python - requests
```
import requests
import json
endpoint = search
host = "http://127.0.0.1:5000/"

payload = {
    "buildNo": "531",
    "testID": "TEST-10",
    "healthCheckResult": "Fail",
    "testComponent": { "$in": ["S3", "Motr", "CSM"] },
    "username": "username",
    "password": "password"
}
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("GET", host+endpoint,
                            headers=headers, data=json.dumps(payload))

print(response.text)
```

#### HTTP Status Code:
|Code | Description |
|-----|-------|
|200 | Success |
|400 | Bad Request: Missing parameters. Do not retry. |
|401 | Unauthorized: Wrong username/password. |
|403 | Forbidden: User does not have permission for operation. |
|404 | Not Found: No entry for that query in MongoDB. |
|503 | Service Unavailable: Unable to connect to mongoDB. |

### 3. update
* Can be used to update previous execution entries in database
* Include `filter` and `update` as dictionary in json body
  (More examples can be seen at [db-collection-updatemany](https://docs.mongodb.com/manual/reference/method/db.collection.updateMany/#db-collection-updatemany))

#### Examples:
1. Command line
```
curl -L -X PATCH 'http://127.0.0.1:5000/update' \
-H 'Content-Type: application/json' \
--data-raw '{
    "filter": {"buildType": "Beta"},
    "update": {"$set": {"buildType": "Release", "OSVersion": "Redhat"}},
    "username": "username",
    "password": "password"
}'
```
2. python - requests
```
import requests
import json
endpoint = update
host = "http://127.0.0.1:5000/"

payload = {
    "filter": {"buildType": "Beta"},
    "update": {"$set": {"buildType": "Release", "OSVersion": "Redhat"}},
    "username": "username",
    "password": "password"
}
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("PATCH", host+endpoint,
                            headers=headers, data=json.dumps(payload))

print(response.text)
```

#### HTTP Status Code:
|Code | Description |
|-----|-------|
|200 | Success |
|400 | Bad Request: Missing parameters. Do not retry. |
|401 | Unauthorized: Wrong username/password. |
|403 | Forbidden: User does not have permission for operation. |
|503 | Service Unavailable: Unable to connect to mongoDB. |