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
#

"""IO Driver module."""

import os
import shutil
import logging

from config.io import CMN_CFG
from commons.helpers.health_helper import Health
from commons.utils import support_bundle_utils as sb


LOGGER = logging.getLogger(__name__)
NODES = CMN_CFG["nodes"]


def check_cluster_services():
    """Check the cluster services."""
    LOGGER.info("Check cluster status for all nodes.")
    response = False, None
    try:
        for node in NODES:
            if node.get("node_type", None).lower() != "master":
                continue
            hostname = node['hostname']
            health = Health(hostname=hostname, username=node['username'], password=node['password'])
            response = health.check_node_health()
            health.disconnect()
            if not response[0]:
                LOGGER.critical(
                    'Cluster Node {%s} failed in health check. Reason: {%s}', hostname, response)
                raise IOError(response[1])
        LOGGER.info("Cluster status is healthy.")
    except OSError as error:
        LOGGER.error("An error occurred in check_cluster_services: %s", str(error))
        response = False, error

    return response


def check_cluster_space():
    """Check nodes space and accepts till 98 % occupancy."""
    LOGGER.info("Check cluster storage for all nodes.")
    try:
        ha_used_percent = 0.0
        for node in NODES:
            if node.get("node_type", None).lower() != "master":
                continue
            hostname = node['hostname']
            health = Health(hostname=hostname, username=node['username'], password=node['password'])
            ha_total, ha_avail, ha_used = health.get_sys_capacity()
            LOGGER.info("Total capacity: %s GB", ha_total / (1024**3))
            LOGGER.info("Available capacity: %s GB", ha_avail / (1024**3))
            LOGGER.info("Used capacity: %s GB", ha_used / (1024**3))
            ha_used_percent = round((ha_used / ha_total) * 100, 1)
            health.disconnect()
            if ha_used_percent > 98.0:
                raise IOError(f'Cluster Node {hostname} failed space {ha_used_percent} check.')
        response = True, ha_used_percent
    except OSError as error:
        LOGGER.error("An error occurred in check_cluster_space: %s", str(error))
        response = False, error

    return response


def collect_support_bundle():
    """Collect support bundles from various components using support bundle cmd."""
    try:
        bundle_dir = os.path.join(os.getcwd(), "support_bundle")
        bundle_name = "io-stability"
        if os.path.exists(bundle_dir):
            LOGGER.info("Removing existing directory %s", bundle_dir)
            shutil.rmtree(bundle_dir)
        os.mkdir(bundle_dir)
        if CMN_CFG["product_family"] == "LC":
            sb.collect_support_bundle_k8s(local_dir_path=bundle_dir)
        else:
            sb.create_support_bundle_single_cmd(bundle_dir, bundle_name)
        bundle_fpath = os.path.join(bundle_dir, os.listdir(bundle_dir)[-1])
    except OSError as error:
        LOGGER.error("An error occurred in collect_support_bundle: %s", error)
        return False, error

    return os.path.exists(bundle_fpath), bundle_fpath


def collect_crash_files():
    """Collect crash files from existing locations."""
    try:
        crash_dir = os.path.join(os.getcwd(), "crash_files")
        if os.path.exists(crash_dir):
            LOGGER.info("Removing existing directory %s", crash_dir)
            shutil.rmtree(crash_dir)
        os.mkdir(crash_dir)
        if CMN_CFG["product_family"] == "LC":
            sb.collect_crash_files_k8s(local_dir_path=crash_dir)
        else:
            sb.collect_crash_files(crash_dir)
        crash_fpath = os.path.join(crash_dir, os.listdir(crash_dir)[-1])
    except OSError as error:
        LOGGER.error("An error occurred in collect_support_bundle: %s", error)
        return False, error

    return os.path.exists(crash_fpath), crash_fpath
