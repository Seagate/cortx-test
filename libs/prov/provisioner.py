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
Provisioner utiltiy methods
"""

import logging
import time
import jenkins
from commons import constants as common_cnst
from commons import params as prm
from commons import pswdmanager

LOGGER = logging.getLogger(__name__)


def build_job(
        job_name: str,
        parameters: dict = None,
        token: str = None) -> dict:
    """
    Helper function to start the jenkins job.
    :param job_name: Name of the jenkins job
    :param parameters: Dict of different parameters to be passed
    :param token: Authentication Token for jenkins job
    :return: build info dict
    """
    username = pswdmanager.decrypt(common_cnst.JENKINS_USERNAME)
    password = pswdmanager.decrypt(common_cnst.JENKINS_PASSWORD)
    jenkins_server_obj = jenkins.Jenkins(
        prm.JENKINS_URL, username=username, password=password)
    LOGGER.debug("Jenkins_server obj: %s", jenkins_server_obj)
    completed_build_number = jenkins_server_obj.get_job_info(
        job_name)['lastCompletedBuild']['number']
    next_build_number = jenkins_server_obj.get_job_info(job_name)[
        'nextBuildNumber']
    LOGGER.info(
        "Last Completed build number: %d and  Next build number: %d",
        completed_build_number,
        next_build_number)
    jenkins_server_obj.build_job(job_name, parameters=parameters, token=token)
    time.sleep(10)
    LOGGER.info("Running the deployment job")
    while True:
        if jenkins_server_obj.get_job_info(job_name)['lastCompletedBuild']['number'] == \
                jenkins_server_obj.get_job_info(job_name)['lastBuild']['number']:
            break
    build_info = jenkins_server_obj.get_build_info(job_name, next_build_number)
    console_output = jenkins_server_obj.get_build_console_output(
        job_name, next_build_number)
    LOGGER.debug("console output:\n %s", console_output)
    return build_info
