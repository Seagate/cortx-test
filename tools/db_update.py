# -*- coding: utf-8 -*-
# !/usr/bin/python
"""Script to update results of manual test execution into database."""
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

# Basic algorithm
# for each TE:
#     for each Test in TE:
#         if test status is TODO
#             Continue
#         result = Search DB by ('buildNo', 'testExecutionID', 'testID', 'valid': True)
#         if no entries in DB :
#             Create one entry in DB
#         else :
#             Patch all present entries to add valid key as false
#             Insert new entry with latest data from JIRA
#         if test status if FAIL:
#             Get bug from JIRA an update in DB

import argparse
import configparser
import json
import logging
import sys
from argparse import RawDescriptionHelpFormatter
from http import HTTPStatus

import requests

from report import jira_api

headers = {
    'Content-Type': 'application/json'
}

logger = logging.getLogger('db_update')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('db_update.log')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
# add the handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)

config = configparser.ConfigParser()
config.read('config.ini')
try:
    HOSTNAME = config["REST"]["hostname"]
    HOSTNAME = HOSTNAME + "reportsdb/"
    DB_USERNAME = config["REST"]["db_username"]
    DB_PASSWORD = config["REST"]["db_password"]
except KeyError:
    logger.error("Could not start DB Update script. Please verify config.ini file")
    sys.exit(1)


def patch_db_request(payload: dict) -> None:
    """
    Description: Make a patch request to database using REST API

    Args:
        payload (dict): Payload data
    """
    request = "PATCH"
    endpoint = "update"

    payload["db_username"] = DB_USERNAME
    payload["db_password"] = DB_PASSWORD

    response = requests.request(request, HOSTNAME + endpoint, headers=headers,
                                data=json.dumps(payload))
    if response.status_code != HTTPStatus.OK:
        logger.error('%s on %s failed\nHEADERS=%s\nBODY=%s\nRESPONSE=%s', request, HOSTNAME +
                     endpoint, response.request.headers, response.request.body, response.text)
        sys.exit(1)


def create_db_request(payload: dict) -> None:
    """
    Description: Make a create request to database using REST API

    Args:
        payload (dict): Payload data
    """
    request = "POST"
    endpoint = "create"

    payload["db_username"] = DB_USERNAME
    payload["db_password"] = DB_PASSWORD

    response = requests.request(request, HOSTNAME + endpoint, headers=headers,
                                data=json.dumps(payload))
    if response.status_code != HTTPStatus.OK:
        logger.error('%s on %s failed\nHEADERS=%s\nBODY=%s\nRESPONSE=%s', request, HOSTNAME +
                     endpoint, response.request.headers, response.request.body, response.text)
        sys.exit(1)


def search_db_request(payload: dict):
    """
    Description: Make a search request to database using REST API

    Args:
        payload (dict): Payload data

    Returns:
        Search result
    """
    request = "GET"
    endpoint = "search"

    payload["db_username"] = DB_USERNAME
    payload["db_password"] = DB_PASSWORD

    response = requests.request(request, HOSTNAME + endpoint, headers=headers,
                                data=json.dumps(payload))
    if response.status_code == HTTPStatus.OK:
        return response.json()["result"]
    if response.status_code == HTTPStatus.NOT_FOUND and "No results" in response.text:
        return None
    logger.error('%s on %s failed\nHEADERS=%s\nBODY=%s\nRESPONSE=%s', request, HOSTNAME +
                 endpoint, response.request.headers, response.request.body, response.text)
    sys.exit(1)


def get_latest_test_plans_from_db() -> list:
    """Get latest 5 test plans from DB"""
    endpoint = "aggregate"
    payload = {"aggregate": [
        {"$group": {"_id": {"testPlanID": "$testPlanID"},
                    "testStartTime": {"$min": "$testStartTime"}}},
        {"$sort": {"testStartTime": -1}}],
        "db_username": DB_USERNAME,
        "db_password": DB_PASSWORD}
    response = requests.request("GET", HOSTNAME + endpoint, headers=headers,
                                data=json.dumps(payload))
    tp_list = []
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        for each in json_response["result"][:5]:
            tp_list.append(each["_id"]["testPlanID"])
    logger.info("Latest 5 test plans from DB: %s", tp_list)
    return tp_list


def parse_argument():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
        description="For syncing a given test plan, pass `only <testplan>` options "
                    "\nFor syncing latest 5 test plans, no options are needed",
        formatter_class=RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='subcommand')

    # sub-parser for only
    parser_only = subparsers.add_parser('only')
    parser_only.add_argument('tp', help='Testplan for build')

    args = parser.parse_args()
    if args.subcommand:
        logger.info("Will sync %s test plan from JIRA to DB", args.tp)
        return [args.tp]
    logger.info("No options passed. Will sync last 5 test plans.")
    return None


# pylint: disable-msg=too-many-locals
# pylint: disable-msg=too-many-nested-blocks
# pylint: disable-msg=too-many-statements
# pylint: disable-msg=too-many-branches
def main():
    """Update test executions from JIRA to MongoDB."""
    args = parse_argument()
    if args:
        tp_keys = args
    else:
        tp_keys = get_latest_test_plans_from_db()

    for tp_key in tp_keys:
        logger.info("JIRA DB Sync for Test Plan ID = %s", tp_key)
        username, password = jira_api.get_username_password()
        tp_details = jira_api.get_details_from_test_plan(tp_key, username, password)
        test_executions = jira_api.get_test_executions_from_test_plan(tp_key,
                                                                      username, password)
        test_plan_issue = jira_api.get_issue_details(tp_key, username, password)
        test_plan_label = test_plan_issue.fields.labels[0] if \
            test_plan_issue.fields.labels else "None"

        # for each TE:
        for test_execution in test_executions:
            logger.info("-Test Execution %s", test_execution["key"])
            test_execution_issue = jira_api.get_issue_details(test_execution["key"],
                                                              username, password)
            test_execution_label = test_execution_issue.fields.labels[0] if \
                test_execution_issue.fields.labels else "None"
            test_team = test_execution_issue.fields.components[0].name if \
                test_execution_issue.fields.components else "CortxQA"

            tests = jira_api.get_test_from_test_execution(test_execution["key"],
                                                          username, password)
            # for each Test in TE:
            for test in tests:
                logger.info("-Test Key %s", test["key"])
                if test["status"] == "TODO":
                    continue
                query_payload = {
                    "query": {
                        "buildNo": tp_details["buildNo"],
                        "testExecutionID": test_execution["key"],
                        "testID": test["key"],
                        "latest": True
                    },
                }

                test_issue = jira_api.get_issue_details(test["key"], username, password)
                feature = test_issue.fields.customfield_21087.value if \
                    test_issue.fields.customfield_21087 else "None"
                feature_id = test_issue.fields.customfield_22881 if \
                    test_issue.fields.customfield_22881 else ["None"]
                dr_id = test_issue.fields.customfield_22882 if \
                    test_issue.fields.customfield_22882 else ["None"]
                log_path = test["comment"] if "comment" in test else "None"

                results = search_db_request(query_payload)

                if not results:
                    logger.debug("DB entry does not exist for build %s TE %s Test %s",
                                 tp_details["buildNo"], test_execution["key"], test["key"])
                    # add one entry
                    payload = {
                        # Framework/Unknown data
                        "clientHostname": "",
                        "noOfNodes": 0,
                        "OSVersion": "",
                        "nodesHostname": [""],
                        "testTags": [""],
                        "testType": "",
                        "testExecutionTime": 0,
                        "healthCheckResult": "",
                        # Data from JIRA
                        "testStartTime": test["startedOn"],
                        "logPath": log_path,
                        "testResult": test["status"],
                        "platformType": tp_details["platformType"],
                        "serverType": tp_details["serverType"],
                        "enclosureType": tp_details["enclosureType"],
                        "testName": test_issue.fields.summary,
                        "testID": test["key"],
                        "testIDLabels": test_issue.fields.labels,
                        "testPlanID": tp_key,
                        "testExecutionID": test_execution["key"],
                        "testPlanLabel": test_plan_label,
                        "testExecutionLabel": test_execution_label,
                        "testTeam": test_team,
                        "buildType": tp_details["branch"],
                        "buildNo": tp_details["buildNo"],
                        "executionType": test_issue.fields.customfield_20981.value,
                        "feature": feature,
                        "latest": True,
                        "drID": dr_id,
                        "featureID": feature_id
                    }
                    create_db_request(payload)
                    logger.debug("Created an entry in DB.")
                else:
                    # if test status in db != in JIRA or no entry in db
                    if results[0]["testResult"].lower() != test["status"].lower():
                        logger.debug("Test Result from DB & JIRA are not matching for Test %s",
                                     test["key"])
                        feature_id = test_issue.fields.customfield_22881 if \
                            test_issue.fields.customfield_22881 else ["None"]
                        dr_id = test_issue.fields.customfield_22882 if \
                            test_issue.fields.customfield_22882 else ["None"]
                        # Add valid key in entry false
                        patch_payload = {
                            "filter": query_payload["query"],
                            "update": {
                                "$set": {"latest": False}
                            }
                        }
                        patch_db_request(patch_payload)
                        logger.debug("Patched old entries with latest false.")
                        # Insert new entry with latest data from JIRA
                        payload = {
                            # Unknown data
                            "clientHostname": "",
                            "noOfNodes": 0,
                            "OSVersion": "",
                            "nodesHostname": [""],
                            "testExecutionTime": 0,
                            "healthCheckResult": "",
                            # Data from JIRA
                            "testStartTime": test["startedOn"],
                            "logPath": log_path,
                            "testResult": test["status"],
                            "platformType": tp_details["platformType"],
                            "serverType": tp_details["serverType"],
                            "enclosureType": tp_details["enclosureType"],
                            "drID": dr_id,
                            "featureID": feature_id,
                            # Data from previous database entry
                            "testTags": results[0]["testTags"],
                            "testType": results[0]["testType"],
                            "testName": results[0]["testName"],
                            "testID": results[0]["testID"],
                            "testIDLabels": results[0]["testIDLabels"],
                            "testPlanID": results[0]["testPlanID"],
                            "testExecutionID": results[0]["testExecutionID"],
                            "testPlanLabel": results[0]["testPlanLabel"],
                            "testExecutionLabel": results[0]["testExecutionLabel"],
                            "testTeam": results[0]["testTeam"],
                            "buildType": results[0]["buildType"],
                            "buildNo": tp_details["buildNo"],
                            "executionType": results[0]["executionType"],
                            "feature": results[0]["feature"],
                            "latest": True,
                        }
                        create_db_request(payload)
                        logger.debug("Created new entry with results from JIRA.")

                if "fail" in test["status"].lower():
                    logger.debug("TEST status is FAIL in JIRA.")
                    # Get BUG ID from JIRA
                    if len(test["defects"]) == 0:
                        logger.warning("Failure is not mapped to any BUG in JIRA TEST - %s, Test "
                                       "Execution - %s, Test Plan = %s",
                                       test["key"], test_execution["key"], tp_key)
                    else:
                        defects = [defect["key"] for defect in test["defects"]]
                        if defects:
                            # PATCH issue in db entry
                            patch_payload = {
                                "filter": query_payload["query"],
                                "update": {
                                    "$set": {"issueIDs": defects}
                                }
                            }
                            patch_db_request(patch_payload)
                            logger.debug("Added defects linked in JIRA into DB.")


if __name__ == '__main__':
    main()
