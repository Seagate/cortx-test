import time
import pytest
import logging
from conftest import run_io_async
from libs.di.di_run_man import RunDataCheckManager
from libs.di.di_mgmt_ops import ManagementOPs
import threading


class TestSample:

    log = logging.getLogger(__name__)

    @classmethod
    def setup_class(cls):
        cls.log.info("Setup class")

    def setup_method(self):
        self.log.info("Setup method")

    def teardown_method(self):
        self.log.info("Teardown method")

    @classmethod
    def teardown_class(cls):
        cls.log.info("Teardown class")

    def test_01(self):
        """
        Test to run IO and verify the download sequentially within test
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2, use_cortx_cli=False)
        users = mgm_ops.create_buckets(nbuckets=2, users=users)
        pref_dir = {"prefix_dir": 'test_01'}
        run_man_obj = RunDataCheckManager(users=users)
        run_man_obj.run_io_sequentially(users=users, prefs=pref_dir)
        time.sleep(320)
        assert True, "msg"

    def test_02(self, run_io_async):
        """
        Test to start DI using data_integrity_chk flag in pytest cmd, parallel IO and verification
        Negative scenario: test failure will immediately stop upload and run_io_sync will
        proceed with verification.
        """
        time.sleep(8)
        assert False, "msg"

    @pytest.mark.usefixtures("run_io_async")
    def test_03(self):
        """
        Test to start DI using data_integrity_chk flag in pytest cmd, parallel IO and verification
        positive scenario
        """
        assert True, "msg"

    def test_04(self):
        """
        Test start IO sleep for sometime and verify IO within test sequentially
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=2, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_04'}
        run_data_chk_obj.start_io(
            users=data, buckets=None, files_count=8, prefs=pref_dir)
        time.sleep(660)
        run_data_chk_obj.stop_io(users=data, di_check=True)
        assert True, "msg"

    def test_05(self):
        """
        Test start IO in parallel, set stop event, sleep for sometime and verify IO parallel
        within test. Explicitly an event obj need to be passed from test
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=5, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=4, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_05'}
        event = threading.Event()
        run_data_chk_obj.start_io_async(
            users=data, buckets=None, files_count=65, prefs=pref_dir,
            event=event)
        event.set()
        time.sleep(4)
        print("test", event.is_set())
        run_data_chk_obj.stop_io_async(users=data, di_check=True)
        assert True, "msg"

    def test_07(self):
        """
        Test start IO in parallel, sleep for sometime and stop upload and verify IO parallel
        within test
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=5, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=4, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_07'}
        run_data_chk_obj.start_io_async(
            users=data, buckets=None, files_count=65, prefs=pref_dir)
        time.sleep(4)
        run_data_chk_obj.stop_io_async(users=data, di_check=True,
                                       eventual_stop=True)
        assert True, "msg"

    def test_08(self):
        """
        Test start IO in parallel, sleep for sometime and stop upload and verify IO parallel
        within test. Use RunDataCheckManager event for an immediate stop
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=5, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=4, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_08'}
        run_data_chk_obj.start_io_async(
            users=data, buckets=None, files_count=35, prefs=pref_dir)
        run_data_chk_obj.event.set()
        time.sleep(4)
        print("test", run_data_chk_obj.event.is_set())
        run_data_chk_obj.stop_io_async(users=data, di_check=True)
        assert True, "msg"

    def test_09(self):
        """
        Test start IO sleep for sometime and stop upload and verify IO within Test
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=2, users=users,
                                      use_cortxcli=True)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_09'}
        run_data_chk_obj.start_io(
            users=data, buckets=None, files_count=8, prefs=pref_dir)
        time.sleep(8)
        run_data_chk_obj.stop_io(users=data, di_check=True, eventual_stop=True)
        assert True, "msg"

    def test_10(self):
        """
        Test start IO sleep for sometime and stop upload and verify IO within Test
        negative scenario: test will be marked as failed
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=2, users=users,
                                      use_cortxcli=True)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_09'}
        run_data_chk_obj.start_io(
            users=data, buckets=None, files_count=8, prefs=pref_dir)
        time.sleep(8)
        run_data_chk_obj.stop_io(users=data, di_check=True, eventual_stop=True)
        assert False, "msg"

    def test_11(self):
        """
        Test start IO in parallel, sleep for sometime and stop upload and verify IO parallel
        within test. Use RunDataCheckManager event for an immediate stop.
        Negative scenario: Test will be marked as failed but parallel IO will be stopped completing
        IO
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=5, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=4, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_08'}
        run_data_chk_obj.start_io_async(
            users=data, buckets=None, files_count=35, prefs=pref_dir)
        run_data_chk_obj.event.set()
        time.sleep(4)
        print("test", run_data_chk_obj.event.is_set())
        run_data_chk_obj.stop_io_async(users=data, di_check=True)
        assert False, "msg"

    def test_12(self):
        """
        Test start IO in parallel, sleep for sometime and stop upload and verify IO parallel
        within test.
        Negative Scenario: test will be marked as failed upload will be stopped before failure
        download will continue for sometime.
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=5, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=4, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_07'}
        run_data_chk_obj.start_io_async(
            users=data, buckets=None, files_count=65, prefs=pref_dir)
        time.sleep(4)
        run_data_chk_obj.stop_io_async(users=data, di_check=True,
                                       eventual_stop=True)
        assert False, "msg"
