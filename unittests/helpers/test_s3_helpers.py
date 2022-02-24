#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest module to test s3 helper."""

import os
import shutil
import logging
import pytest

from config import CMN_CFG as CM_CFG
from config.s3 import S3_CFG
from libs.s3 import S3H_OBJ
from commons.helpers.s3_helper import S3Helper


class TestS3helper:
    """Test S3 helper class."""

    @classmethod
    def setup_class(cls) -> None:
        """Suite level setup."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Test suite level setup started.")
        cls.slapd_service_flg = False
        cls.enable_instances = False
        cls.access_key = "alfjkalfjiecnk@#&kafjkancsmnc"
        cls.log.info("Access key: %s", cls.access_key)
        cls.secret_access_key = "*HSLKJMDqpowdapofmamcamc"
        cls.log.info("Secret key: %s", cls.secret_access_key)
        cls.slapd_service = "slapd"
        cls.log.info("slapd_service: %s", cls.slapd_service)
        cls.s3cfg_path = S3_CFG["s3cfg_path"]
        cls.s3cfg_path_bk = f"{cls.s3cfg_path}.bk"
        cls.log.info("s3cfg_path: %s", cls.s3cfg_path)
        if os.path.isfile(cls.s3cfg_path):
            os.rename(cls.s3cfg_path, cls.s3cfg_path_bk)
        cls.s3fs_path = S3_CFG["s3fs_path"]
        cls.s3fs_path_bk = f"{cls.s3fs_path}.bk"
        cls.log.info("s3fs_path: %s", cls.s3fs_path)
        if os.path.isfile(cls.s3fs_path):
            os.rename(cls.s3fs_path, cls.s3cfg_path_bk)
        cls.minio_path = S3_CFG["minio_path"]
        cls.minio_path_bk = f"{cls.minio_path}.bk"
        cls.log.info("minio_path: %s", cls.minio_path)
        if os.path.exists(cls.minio_path):
            shutil.copy(cls.minio_path, cls.minio_path_bk)
        cls.s3_config_path = "/opt/seagate/cortx/s3/conf/s3config.yaml"
        cls.log.info("s3_config_path: %s", cls.s3_config_path)
        cls.local_path = os.path.join(os.getcwd(), "s3config.yaml")
        cls.log.info("local_path: %s", cls.local_path)
        cls.log.info("ENDED: Test suite level setup completed.")

    @classmethod
    def teardown_class(cls) -> None:
        """Suite level teardown."""
        cls.log.info("STARTED: Test suite level teardown started.")
        if os.path.isfile(cls.s3cfg_path_bk):
            os.rename(cls.s3cfg_path_bk, cls.s3cfg_path)
        if os.path.isfile(cls.s3fs_path_bk):
            os.rename(cls.s3fs_path_bk, cls.s3cfg_path)
        if os.path.exists(cls.minio_path_bk):
            os.rename(cls.minio_path_bk, cls.minio_path)
        cls.log.info(
            "Restored: %s, %s, %s",
            cls.s3cfg_path,
            cls.s3fs_path,
            cls.minio_path)
        if not cls.slapd_service_flg:
            status, resp = S3H_OBJ.restart_s3server_service(cls.slapd_service)
            cls.log.info("status: %s, response: %s", status, resp)
            assert status, resp
            status, resp = S3H_OBJ.restart_s3server_service(
                cls.slapd_service, CM_CFG["nodes"][0]['fqdn'])
            cls.log.info("status: %s, response: %s", status, resp)
            assert status, resp
        if not cls.enable_instances:
            status, resp = S3H_OBJ.enable_disable_s3server_instances(
                resource_disable=False)
            cls.log.info("status: %s, response: %s", status, resp)
            # assert status, resp
        cls.log.info("ENDED: Test suite level teardown completed.")

    def setup_method(self):
        """Test case setup."""
        self.log.info("START: Test case setup started.")
        if os.path.exists(self.local_path):
            os.remove(self.local_path)
        self.log.info("Removed: %s", self.local_path)
        self.log.info("END: Test case setup completed.")

    def teardown_method(self):
        """Test case teardown."""
        self.log.info("START: Test case teardown started.")
        if os.path.exists(self.local_path):
            os.remove(self.local_path)
        self.log.info("Removed: %s", self.local_path)
        self.log.info("END: Test case teardown completed.")

    @pytest.mark.s3unittest
    def test_s3helper_singleton(self) -> None:
        """Test s3helper is singleton."""
        self.log.info("START: Test S3helper is singleton.")
        try:
            s3h1 = S3Helper()
            assert S3Helper, f"S3Helper is not singleton: {s3h1}"
        except ImportError as ierr:
            self.log.info(ierr)
            self.log.info("S3Helper is a singleton object.")
        s3h1 = S3Helper.get_instance()
        self.log.info(s3h1)
        assert s3h1 == S3H_OBJ, f"Instances are not matching: {S3H_OBJ}, {s3h1}"
        s3h2 = S3Helper.get_instance()
        self.log.info(s3h2)
        assert s3h2 == s3h1, f"Instances are not matching: {s3h1}, {s3h2}"
        self.log.info("END: Tested S3helper is singleton.")

    @pytest.mark.s3unittest
    def test_configure_s3cfg(self):
        """Test configure s3cfg."""
        self.log.info("START: Test configure s3cfg.")
        resp = S3H_OBJ.configure_s3cfg(
            self.access_key,
            self.secret_access_key,
            self.s3cfg_path)
        self.log.info(resp)
        assert resp, f"Failed to create s3cfg status: {resp}, path: {self.s3cfg_path}"
        assert os.path.isfile(
            self.s3cfg_path), f"Path not exists: {self.s3cfg_path}"
        self.log.info("END: Tested configure s3cfg.")

    @pytest.mark.s3unittest
    def test_configure_s3fs(self):
        """Test configure s3fs."""
        self.log.info("START: Test configure s3fs.")
        resp = S3H_OBJ.configure_s3fs(
            self.access_key,
            self.secret_access_key,
            self.s3fs_path)
        self.log.info(resp)
        assert resp, f"Failed to create s3fs status: {resp}, path: {self.s3fs_path}"
        assert os.path.isfile(
            self.s3fs_path), f"Path not exists: {self.s3fs_path}"
        self.log.info("END: Tested configure s3fs.")

    @pytest.mark.s3unittest
    def test_check_s3services_online(self):
        """Test check s3services online."""
        self.log.info("START: Test check s3services online.")
        status, resp = S3H_OBJ.check_s3services_online()
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.check_s3services_online(host=CM_CFG["nodes"][0]['fqdn'])
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.check_s3services_online(user="xyz")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        status, resp = S3H_OBJ.check_s3services_online(
            host=CM_CFG["nodes"][0]['fqdn'], pwd="qawzsx")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        self.log.info("END: Tested check s3services online.")

    @pytest.mark.s3unittest
    def test_get_s3server_service_status(self):
        """Test get s3server service status."""
        self.log.info("START: Test get s3server service status.")
        status, resp = S3H_OBJ.get_s3server_service_status(
            service=self.slapd_service)
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.get_s3server_service_status(
            service=self.slapd_service, host=CM_CFG["host2"])
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.get_s3server_service_status(
            service=self.slapd_service, user="xyz")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        status, resp = S3H_OBJ.get_s3server_service_status(
            service=self.slapd_service, pwd="Qawzsx")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        self.log.info("END: Tested get s3server service status.")

    @pytest.mark.s3unittest
    def test_stop_s3server_service(self):
        """Test stop s3server service."""
        self.log.info("START: Test stop s3server service.")
        status, resp = S3H_OBJ.stop_s3server_service(self.slapd_service)
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.stop_s3server_service(
            self.slapd_service, CM_CFG["host2"])
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.stop_s3server_service("xyz")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        self.slapd_service_flg = True
        self.log.info("END: Tested stop s3server service.")

    @pytest.mark.s3unittest
    def test_start_s3server_service(self):
        """Test start s3server service."""
        self.log.info("START: Test start s3server service.")
        status, resp = S3H_OBJ.start_s3server_service(self.slapd_service)
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.start_s3server_service(
            self.slapd_service, CM_CFG["host2"])
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.start_s3server_service("xyz")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        self.log.info("END: Tested start s3server service.")

    @pytest.mark.s3unittest
    def test_restart_s3server_service(self):
        """Test restart s3server service status."""
        self.log.info("START: Test restart s3server service status.")
        status, resp = S3H_OBJ.restart_s3server_service(
            service=self.slapd_service)
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_service(
            service=self.slapd_service, host=CM_CFG["host2"])
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_service(
            service=self.slapd_service, pwd="Qawzsx")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        status, resp = S3H_OBJ.restart_s3server_service(service="abc")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        self.log.info("END: Tested restart s3server service status.")

    @pytest.mark.s3unittest
    def test_restart_s3server_processes(self):
        """Test restart s3server processes."""
        self.log.info("START: Test restart s3server processes.")
        status, resp = S3H_OBJ.restart_s3server_processes()
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_processes(host=CM_CFG["host2"])
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_processes(user="xyz")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        self.log.info("END: Tested restart s3server processes.")

    @pytest.mark.s3unittest
    def test_get_s3server_resource(self):
        """Test get s3server resource."""
        self.log.info("START: Test get s3server resource")
        status, resp = S3H_OBJ.get_s3server_resource()
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.get_s3server_resource(host=CM_CFG["host2"])
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.get_s3server_resource(user="xyz")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        self.log.info("END: Tested get s3server resource")

    @pytest.mark.s3unittest
    def test_restart_s3server_resources(self):
        """Test restart s3server resources."""
        self.log.info("START: Test restart s3server resources.")
        status, resp = S3H_OBJ.restart_s3server_resources()
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_resources(host=CM_CFG["host2"])
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_resources(user="xyz")
        self.log.info("status: %s, response: %s", status, resp)
        assert not status, resp
        self.log.info("END: Tested restart s3server resources.")

    @pytest.mark.s3unittest
    def test_get_s3server_fids(self):
        """Test get s3server fids."""
        self.log.info("START: Test get s3server fids.")
        status, resp = S3H_OBJ.get_s3server_fids()
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        self.log.info("END: Tested get s3server fids.")

    @pytest.mark.s3unittest
    def test_enable_disable_s3server_instances(self):
        """Test enable disable s3server instances."""
        self.log.info("START: Test enable disable s3server instance.")
        status, resp = S3H_OBJ.enable_disable_s3server_instances(
            resource_disable=True)
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.enable_disable_s3server_instances(
            resource_disable=False)
        self.log.info("status: %s, response: %s", status, resp)
        assert status, resp
        self.enable_instances = True
        self.log.info("END: Tested enable disable s3server instance.")

    @pytest.mark.s3unittest
    def test_configure_minio(self):
        """Test configure minio."""
        self.log.info("START: Test configure minio.")
        status = S3H_OBJ.configure_minio(
            access=self.access_key,
            secret=self.secret_access_key,
            path=self.minio_path)
        self.log.info("status: %s", status)
        assert status, "Failed to get access, secert keys from {}".format(
            self.minio_path)
        self.log.info("END: Tested configure minio.")

    @pytest.mark.s3unittest
    def test_get_local_keys(self):
        """Test get local keys."""
        self.log.info("START: Test get local keys.")
        access, secret = S3H_OBJ.get_local_keys()
        self.log.info("Keys: access: %s, secret: %s", access, secret)
        assert access, secret
        access, secret = S3H_OBJ.get_local_keys(section="xyz")
        self.log.info("Keys: access: %s, secret: %s", access, secret)
        assert not access, secret
        self.log.info("END: Tested get local keys.")
