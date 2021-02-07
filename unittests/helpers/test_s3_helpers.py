#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest module to test s3 helper."""

import os
import shutil
import logging
import pytest

from commons.helpers.s3_helper import S3Helper
from commons.utils.config_utils import read_yaml

LOGGER = logging.getLogger(__name__)

try:
    S3H_OBJ = S3Helper()
except ImportError as ierr:
    LOGGER.warning(str(ierr))
    S3H_OBJ = S3Helper.get_instance()

CM_CFG = read_yaml("config/common_config.yaml")[1]


class TestS3helper:
    """Test S3 helper class."""

    @classmethod
    def setup_class(cls) -> None:
        """Suite level setup."""
        LOGGER.info("STARTED: Test suite level setup started.")
        cls.slapd_service_flg = False
        cls.enable_instances = False
        cls.access_key = "alfjkalfjiecnk@#&kafjkancsmnc"
        LOGGER.info("Access key: %s", cls.access_key)
        cls.secret_access_key = "*HSLKJMDqpowdapofmamcamc"
        LOGGER.info("Secret key: %s", cls.secret_access_key)
        cls.slapd_service = "slapd"
        LOGGER.info("slapd_service: %s", cls.slapd_service)
        cls.s3cfg_path = CM_CFG["s3cfg_path"]
        cls.s3cfg_path_bk = f"{cls.s3cfg_path}.bk"
        LOGGER.info("s3cfg_path: %s", cls.s3cfg_path)
        if os.path.isfile(cls.s3cfg_path):
            os.rename(cls.s3cfg_path, cls.s3cfg_path_bk)
        cls.s3fs_path = CM_CFG["s3fs_path"]
        cls.s3fs_path_bk = f"{cls.s3fs_path}.bk"
        LOGGER.info("s3fs_path: %s", cls.s3fs_path)
        if os.path.isfile(cls.s3fs_path):
            os.rename(cls.s3fs_path, cls.s3cfg_path_bk)
        cls.minio_path = CM_CFG["minio_path"]
        cls.minio_path_bk = f"{cls.minio_path}.bk"
        LOGGER.info("minio_path: %s", cls.minio_path)
        if os.path.exists(cls.minio_path):
            shutil.copy(cls.minio_path, cls.minio_path_bk)
        cls.s3_config_path = "/opt/seagate/cortx/s3/conf/s3config.yaml"
        LOGGER.info("s3_config_path: %s", cls.s3_config_path)
        cls.local_path = "/home/s3config.yaml"
        LOGGER.info("local_path: %s", cls.local_path)
        LOGGER.info("ENDED: Test suite level setup completed.")

    @classmethod
    def teardown_class(cls) -> None:
        """Suite level teardown."""
        LOGGER.info("STARTED: Test suite level teardown started.")
        if os.path.isfile(cls.s3cfg_path_bk):
            os.rename(cls.s3cfg_path_bk, cls.s3cfg_path)
        if os.path.isfile(cls.s3fs_path_bk):
            os.rename(cls.s3fs_path_bk, cls.s3cfg_path)
        if os.path.exists(cls.minio_path_bk):
            os.rename(cls.minio_path_bk, cls.minio_path)
        LOGGER.info("Restored: %s, %s, %s", cls.s3cfg_path, cls.s3fs_path, cls.minio_path)
        if not cls.slapd_service_flg:
            status, resp = S3H_OBJ.restart_s3server_service(cls.slapd_service)
            LOGGER.info("status: %s, response: %s", status, resp)
            assert status, resp
            status, resp = S3H_OBJ.restart_s3server_service(
                cls.slapd_service, CM_CFG["host2"])
            LOGGER.info("status: %s, response: %s", status, resp)
            assert status, resp
        if not cls.enable_instances:
            status, resp = S3H_OBJ.enable_disable_s3server_instances(
                resource_disable=False)
            LOGGER.info("status: %s, response: %s", status, resp)
            assert status, resp
        LOGGER.info("ENDED: Test suite level teardown completed.")

    def setup_method(self):
        """Test case setup"""
        LOGGER.info("START: Test case setup started.")
        if os.path.exists(self.local_path):
            os.remove(self.local_path)
        LOGGER.info("Removed: %s", self.local_path)
        LOGGER.info("END: Test case setup completed.")

    def teardown_method(self):
        """Test case teardown"""
        LOGGER.info("START: Test case teardown started.")
        if os.path.exists(self.local_path):
            os.remove(self.local_path)
        LOGGER.info("Removed: %s", self.local_path)
        LOGGER.info("END: Test case teardown completed.")

    @pytest.mark.s3unittest
    def test_s3helper_singleton(self) -> None:
        """Test s3helper is singleton."""
        LOGGER.info("START: Test S3helper is singleton.")
        try:
            s3h1 = S3Helper()
            assert S3Helper, f"S3Helper is not singleton: {s3h1}"
        except ImportError as ierr:
            LOGGER.info(ierr)
            LOGGER.info("S3Helper is a singleton object.")
        s3h1 = S3Helper.get_instance()
        LOGGER.info(s3h1)
        assert s3h1 == S3H_OBJ, f"Instances are not matching: {S3H_OBJ}, {s3h1}"
        s3h2 = S3Helper.get_instance()
        LOGGER.info(s3h2)
        assert s3h2 == s3h1, f"Instances are not matching: {s3h1}, {s3h2}"
        LOGGER.info("END: Tested S3helper is singleton.")

    @pytest.mark.s3unittest
    def test_configure_s3cfg(self):
        """Test configure s3cfg."""
        LOGGER.info("START: Test configure s3cfg.")
        resp = S3H_OBJ.configure_s3cfg(
            self.access_key,
            self.secret_access_key,
            self.s3cfg_path)
        LOGGER.info(resp)
        assert resp, f"Failed to create s3cfg status: {resp}, path: {self.s3cfg_path}"
        assert os.path.isfile(
            self.s3cfg_path), f"Path not exists: {self.s3cfg_path}"
        LOGGER.info("END: Tested configure s3cfg.")

    @pytest.mark.s3unittest
    def test_configure_s3fs(self):
        """Test configure s3fs."""
        LOGGER.info("START: Test configure s3fs.")
        resp = S3H_OBJ.configure_s3fs(
            self.access_key,
            self.secret_access_key,
            self.s3fs_path)
        LOGGER.info(resp)
        assert resp, f"Failed to create s3fs status: {resp}, path: {self.s3fs_path}"
        assert os.path.isfile(
            self.s3fs_path), f"Path not exists: {self.s3fs_path}"
        LOGGER.info("END: Tested configure s3fs.")

    @pytest.mark.s3unittest
    def test_check_s3services_online(self):
        """Test check s3services online."""
        LOGGER.info("START: Test check s3services online.")
        status, resp = S3H_OBJ.check_s3services_online()
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.check_s3services_online(host=CM_CFG["host2"])
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.check_s3services_online(user="xyz")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        status, resp = S3H_OBJ.check_s3services_online(
            host=CM_CFG["host2"], pwd="qawzsx")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested check s3services online.")

    @pytest.mark.s3unittest
    def test_get_s3server_service_status(self):
        """Test get s3server service status."""
        LOGGER.info("START: Test get s3server service status.")
        status, resp = S3H_OBJ.get_s3server_service_status(
            service=self.slapd_service)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.get_s3server_service_status(
            service=self.slapd_service, host=CM_CFG["host2"])
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.get_s3server_service_status(
            service=self.slapd_service, user="xyz")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        status, resp = S3H_OBJ.get_s3server_service_status(
            service=self.slapd_service, pwd="Qawzsx")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested get s3server service status.")

    @pytest.mark.s3unittest
    def test_stop_s3server_service(self):
        """Test stop s3server service."""
        LOGGER.info("START: Test stop s3server service.")
        status, resp = S3H_OBJ.stop_s3server_service(self.slapd_service)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.stop_s3server_service(
            self.slapd_service, CM_CFG["host2"])
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.stop_s3server_service("xyz")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        self.slapd_service_flg = True
        LOGGER.info("END: Tested stop s3server service.")

    @pytest.mark.s3unittest
    def test_start_s3server_service(self):
        """Test start s3server service."""
        LOGGER.info("START: Test start s3server service.")
        status, resp = S3H_OBJ.start_s3server_service(self.slapd_service)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.start_s3server_service(
            self.slapd_service, CM_CFG["host2"])
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.start_s3server_service("xyz")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested start s3server service.")

    @pytest.mark.s3unittest
    def test_restart_s3server_service(self):
        """Test restart s3server service status."""
        LOGGER.info("START: Test restart s3server service status.")
        status, resp = S3H_OBJ.restart_s3server_service(
            service=self.slapd_service)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_service(
            service=self.slapd_service, host=CM_CFG["host2"])
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_service(
            service=self.slapd_service, pwd="Qawzsx")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        status, resp = S3H_OBJ.restart_s3server_service(service="abc")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested restart s3server service status.")

    @pytest.mark.s3unittest
    def test_restart_s3server_processes(self):
        """Test restart s3server processes."""
        LOGGER.info("START: Test restart s3server processes.")
        status, resp = S3H_OBJ.restart_s3server_processes()
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_processes(host=CM_CFG["host2"])
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_processes(user="xyz")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested restart s3server processes.")

    @pytest.mark.s3unittest
    def test_get_s3server_resource(self):
        """Test get s3server resource."""
        LOGGER.info("START: Test get s3server resource")
        status, resp = S3H_OBJ.get_s3server_resource()
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.get_s3server_resource(host=CM_CFG["host2"])
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.get_s3server_resource(user="xyz")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested get s3server resource")

    @pytest.mark.s3unittest
    def test_restart_s3server_resources(self):
        """Test restart s3server resources."""
        LOGGER.info("START: Test restart s3server resources.")
        status, resp = S3H_OBJ.restart_s3server_resources()
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_resources(host=CM_CFG["host2"])
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.restart_s3server_resources(user="xyz")
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested restart s3server resources.")

    @pytest.mark.s3unittest
    def test_is_s3_server_path_exists(self):
        """Test s3 server path exists."""
        LOGGER.info("START: Test s3 server path exists.")
        status, resp = S3H_OBJ.is_s3_server_path_exists(
            path=self.s3_config_path)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.is_s3_server_path_exists(path=self.local_path)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested s3 server path exists.")

    @pytest.mark.s3unittest
    def test_get_s3server_fids(self):
        """Test get s3server fids."""
        LOGGER.info("START: Test get s3server fids.")
        status, resp = S3H_OBJ.get_s3server_fids()
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        LOGGER.info("END: Tested get s3server fids.")

    @pytest.mark.s3unittest
    def test_copy_s3server_file(self):
        """Test copy s3server file."""
        LOGGER.info("START: Test copy s3server file.")
        status, resp = S3H_OBJ.copy_s3server_file(
            file_path=self.local_path, local_path=self.s3_config_path)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        status, resp = S3H_OBJ.copy_s3server_file(
            file_path=self.s3_config_path, local_path=self.s3_config_path)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        status, resp = S3H_OBJ.copy_s3server_file(
            file_path=self.s3_config_path, local_path=self.local_path)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        LOGGER.info("END: Tested copy s3server file.")

    @pytest.mark.s3unittest
    def test_is_string_in_s3server_file(self):
        """Test is string in s3server file."""
        LOGGER.info("START: Test is string in s3server file.")
        status, resp = S3H_OBJ.is_string_in_s3server_file(
            string="syslog", file_path=self.s3_config_path)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.is_string_in_s3server_file(
            string="non-exsting-string", file_path=self.s3_config_path)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested is string in s3server file.")

    @pytest.mark.s3unittest
    def test_enable_disable_s3server_instances(self):
        """Test enable disable s3server instances."""
        LOGGER.info("START: Test enable disable s3server instance.")
        status, resp = S3H_OBJ.enable_disable_s3server_instances(
            resource_disable=True)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.enable_disable_s3server_instances(
            resource_disable=False)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        self.enable_instances = True
        LOGGER.info("END: Tested enable disable s3server instance.")

    @pytest.mark.s3unittest
    def test_configure_minio(self):
        """Test configure minio."""
        LOGGER.info("START: Test configure minio.")
        status = S3H_OBJ.configure_minio(
            access=self.access_key, secret=self.secret_access_key, path=self.minio_path)
        LOGGER.info("status: %s", status)
        assert status, "Failed to get access, secert keys from {}".format(self.minio_path)
        LOGGER.info("END: Tested configure minio.")

    @pytest.mark.s3unittest
    def test_get_local_keys(self):
        """Test get local keys."""
        LOGGER.info("START: Test get local keys.")
        access, secret = S3H_OBJ.get_local_keys()
        LOGGER.info("Keys: access: %s, secret: %s", access, secret)
        assert access, secret
        access, secret = S3H_OBJ.get_local_keys(section="xyz")
        LOGGER.info("Keys: access: %s, secret: %s", access, secret)
        assert not access, secret
        LOGGER.info("END: Tested get local keys.")

    @pytest.mark.s3unittest
    def test_is_string_in_file(self):
        """Test is string in file."""
        LOGGER.info("START: Test is string in file.")
        status, resp = S3H_OBJ.is_string_in_file(
            string="syslog", file_path=self.s3_config_path)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert status, resp
        status, resp = S3H_OBJ.is_string_in_file(
            string="non-existing-string", file_path=self.s3_config_path)
        LOGGER.info("status: %s, response: %s", status, resp)
        assert not status, resp
        LOGGER.info("END: Tested is string in file.")
