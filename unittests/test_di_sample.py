import time
import pytest
import logging
from conftest import run_io_sequentially
from libs.di.di_run_man import RunDataCheckManager
from libs.di.di_mgmt_ops import ManagementOPs
import threading


class TestSample:

    log = logging.getLogger(__name__)

    @classmethod
    def setup_class(cls):
        cls.log.info("I am in setup class")

    def setup_method(self):
        self.log.info("I am in setup method")

    def teardown_method(self):
        self.log.info("I am in teardown method")

    @classmethod
    def teardown_class(cls):
        cls.log.info("I am in Teardown class")

    def test_01(self):
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2, use_cortx_cli=False)
        users = mgm_ops.create_buckets(nbuckets=2, users=users)
        pref_dir = {"prefix_dir": 'test_01'}
        run_io_sequentially(users=users, prefs=pref_dir)
        time.sleep(320)
        assert True, "msg"

    def test_02(self):
        time.sleep(3)
        assert False, "msg"

    def test_03(self):
        assert True, "msg"

    def test_04(self):
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

    @pytest.mark.parametrize(
        "run_io_async", [{'user': 2, 'buckets': 5, 'files_count': 10,
                          'prefs': {'prefix_dir': 'test_06'}}],
        indirect=['run_io_async'])
    def test_06(self):
        time.sleep(6)
        assert True, "msg"

    def test_07(self):
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
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=2, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_09'}
        run_data_chk_obj.start_io(
            users=data, buckets=None, files_count=8, prefs=pref_dir)
        time.sleep(8)
        run_data_chk_obj.stop_io(users=data, di_check=True, eventual_stop=True)
        assert True, "msg"