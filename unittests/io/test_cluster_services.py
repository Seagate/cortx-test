#!/usr/bin/python
# -*- coding: utf-8 -*-
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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

"""UT's for IO cluster services module."""

import unittest
from commons import params
from commons.utils.system_utils import mount_nfs_server
from commons.utils.system_utils import umount_nfs_server
from libs.io import cluster_services
from unittests.io import logger


class ClusterServicesTestCase(unittest.TestCase):
    """Tests suite for cluster service operations."""

    @classmethod
    def setUpClass(cls) -> None:
        """Pre-requisite for test suite operations."""
        logger.info("STARTED: Test suite setup level operations.")
        logger.info("Mount nfs server.")
        status = mount_nfs_server(params.NFS_SERVER_DIR, params.MOUNT_DIR)
        cls.assertTrue(status, "Failed to mount nfs server: {}".format(params.NFS_SERVER_DIR))
        logger.info("Server '%s' mounted successfully.", params.NFS_SERVER_DIR)
        logger.info("ENDED: Test suite setup level operations.")

    @classmethod
    def tearDownClass(cls) -> None:
        """Post-requisite for test suite operations."""
        logger.info("STARTED: Test suite teardown level operations.")
        logger.info("Unmount nfs server.")
        status = umount_nfs_server(params.MOUNT_DIR)
        cls.assertTrue(status, "Failed to unmount nfs server: {}".format(params.NFS_SERVER_DIR))
        logger.info("Server '%s' unmounted successfully.", params.NFS_SERVER_DIR)
        logger.info("ENDED: Test suite teardown level operations.")

    def test_check_cluster_services(self):
        """Test Check cluster services."""
        logger.info("Started: Test Check cluster services.")
        resp = cluster_services.check_cluster_services()
        logger.info(resp)
        self.assertTrue(resp[0], resp[1])
        logger.info("ENDED: Test Check cluster services.")

    def test_check_cluster_space(self):
        """Test check cluster space."""
        logger.info("Started: Test Check cluster space.")
        resp = cluster_services.check_cluster_space()
        logger.info(resp)
        self.assertTrue(resp[0], resp[1])
        logger.info("ENDED: Test Check cluster space.")

    def test_collect_support_bundle(self):
        """Test collect support bundle."""
        logger.info("Started: Test collect support bundle.")
        resp = cluster_services.collect_support_bundle()
        logger.info(resp)
        self.assertTrue(resp[0], resp[1])
        logger.info("ENDED: Test collect support bundle.")

    def test_collect_crash_files(self):
        """Test collect crash files."""
        logger.info("Started: Test collect crash files.")
        resp = cluster_services.collect_crash_files()
        logger.info(resp)
        self.assertTrue(resp[0], resp[1])
        logger.info("ENDED: Test collect crash files.")

    def test_collect_upload_sb_to_nfs_server(self):
        """Test collect upload sb to nfs server."""
        logger.info("STARTED: Test collect upload sb to nfs server.")
        for _ in range(4):
            resp = cluster_services.collect_upload_sb_to_nfs_server(params.MOUNT_DIR, "5403", 4)
            logger.info(resp)
            self.assertTrue(resp[0], resp[1])
        resp = cluster_services.collect_upload_sb_to_nfs_server(params.MOUNT_DIR, "5403", 4)
        logger.info(resp)
        self.assertTrue(resp[0], resp[1])
        resp = cluster_services.collect_upload_sb_to_nfs_server(params.MOUNT_DIR, "5403", 2)
        logger.info(resp)
        self.assertTrue(resp[0], resp[1])
        resp = cluster_services.collect_upload_sb_to_nfs_server(params.MOUNT_DIR, "5403", 3)
        logger.info(resp)
        self.assertTrue(resp[0], resp[1])
        logger.info("ENDED: Test collect upload sb to nfs server.")


if __name__ == '__main__':
    unittest.main()
