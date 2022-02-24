#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""
Create EOS jira bug on failure in Continuous deployment Jenkins Job.
"""
import os

from jira import JIRA


def create_payload(cortx_build, job_name, log_path, jenkins_build_no, jenkins_build_url):
    """
    Create payload for EOS jira creation
    param: cortx_build : Cortx Build number
    param: job_name : Jenkins Job name
    param: log_path: NFS shared path for logs and support bundle created
    param: jenkins_build_no:
    """
    issue_data = dict()
    issue_data['project'] = {'key': 'EOS'}
    issue_data['issuetype'] = {'name': 'Bug'}
    issue_data['priority'] = {'name': 'High'}
    issue_data['versions'] = [{'name': 'CORTX-R2'}]
    issue_data['labels'] = ['CORTX_QA', 'DEPLOY_CICD']
    issue_data['components'] = [{'name': 'CFT'}]
    issue_data['summary'] = f'{job_name} Failed on Build {cortx_build}'
    issue_data['description'] = f'\n {job_name} is failed for the build {cortx_build}. ' \
                                f'\n Please check Jenkins console and deployment log for info.' \
                                f'\n Test Details' \
                                f'\n Cortx build : {cortx_build} ' \
                                f'\n Jenkins Build No : {jenkins_build_no}' \
                                f'\n Jenkins Build URL : {jenkins_build_url}' \
                                f"\n Test logs and support bundle stored at location: {log_path}"
    issue_data["customfield_10122"] = {"value": "CORTX_QA"}  # defect found
    return issue_data


def main():
    """
    Main function for creating eos jira
    """
    jira_id = os.environ['JIRA_ID']
    jira_pswd = os.environ['JIRA_PASSWORD']
    cortx_build = os.environ['BUILD']
    job_name = os.environ['JOB_NAME']
    log_path = os.environ['LOG_PATH']
    jenkins_build_no = os.environ['BUILD_NUMBER']
    jenkins_build_url = os.environ['BUILD_URL']

    payload = create_payload(cortx_build=cortx_build,
                             job_name=job_name,
                             log_path=log_path,
                             jenkins_build_no=jenkins_build_no,
                             jenkins_build_url=jenkins_build_url)
    print(payload)

    jira_url = "https://jts.seagate.com/"
    options = {'server': jira_url}
    auth = (jira_id, jira_pswd)
    auth_jira = JIRA(options, basic_auth=auth)
    issue = auth_jira.create_issue(fields=payload)
    print("ISSUE RAISED : ", issue)


if __name__ == "__main__":
    main()
