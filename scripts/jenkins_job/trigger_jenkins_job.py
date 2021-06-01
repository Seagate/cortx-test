""" Script to Trigger Jenkins Job"""
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


import logging
from commons.utils import assert_utils
from libs.prov.provisioner import Provisioner

JOB_DEPLOY_3N = 'VM-Deployment-R2-3Node'
JOB_DEPLOY_1N = 'VM-Deployment-R2-1Node'
JOB_DESTROY_3N = '3-Node-VM-Destroy'
JEN_DEPLOY_URL = "http://eos-jenkins.colo.seagate.com/job/Cortx-Deployment"
JEN_DESTROY_URL = "http://eos-jenkins.colo.seagate.com/job/Provisioner"

LOGGER = logging.getLogger(__name__)


def trigger_jenkins_job(job_name, jen_url, parameters, token):
    """
    Generic function for any jenkins job trigger
    """
    output = Provisioner.build_job(
        job_name, parameters, token, jen_url)
    LOGGER.info("Jenkins Build URL: {}".format(output['url']))
    assert_utils.assert_equal(
        output['result'],
        "SUCCESS",
        "Job is not successful, please check the url.")


def trigger_deploy_destroy__job(job, hostnames, node_ps, token, build='', mgmt_vip=''):
    """
    Function for triggering 1/3N deployment and destroy jenkins job
    """
    if hostnames:
        job_name = ''
        jenkins_url = ''
        parameters = dict()
        valid_parameters = True
        if job == 'deploy':
            jenkins_url = JEN_DEPLOY_URL
            if len(hostnames) == 1:
                LOGGER.info("1N deployment job will be triggered")
                job_name = JOB_DEPLOY_1N
                parameters['CORTX_BUILD'] = build
                parameters['NODE1'] = hostnames[0]
                parameters['NODE_PASS'] = node_ps
            elif len(hostnames) == 3:
                job_name = JOB_DEPLOY_3N
                LOGGER.info("3N deployment job will be triggered")
                parameters['CORTX_BUILD'] = build
                parameters['NODE1'] = hostnames[0]
                parameters['NODE2'] = hostnames[1]
                parameters['NODE3'] = hostnames[2]
                parameters['NODE_PASS'] = node_ps
                parameters['NODE_MGMT_VIP'] = mgmt_vip
            else:
                valid_parameters = False
        elif job == 'destroy':
            jenkins_url = JEN_DESTROY_URL
            if len(hostnames) == 3:
                LOGGER.info("3N destroy job will be triggered")
                job_name = '3-Node-VM-Destroy'
                parameters['NODE1'] = hostnames[0]
                parameters['NODE2'] = hostnames[1]
                parameters['NODE3'] = hostnames[2]
                parameters['NODE_PASS'] = node_ps
            else:
                valid_parameters = False
        if valid_parameters:
            output = Provisioner.build_job(
                job_name, parameters, token, jenkins_url)
            LOGGER.info("Jenkins Build URL: {}".format(output['url']))
            assert_utils.assert_equal(
                output['result'],
                "SUCCESS",
                "Job is not successful, please check the url.")
        else:
            LOGGER.error("Please check provided parameters")
