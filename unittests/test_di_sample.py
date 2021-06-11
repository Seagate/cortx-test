import time
import pytest
import logging
from conftest import run_io_sequentially
from libs.di.di_run_man import RunDataCheckManager
from libs.di.di_mgmt_ops import ManagementOPs


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
        users = mgm_ops.create_account_users(nusers=2)
        users = mgm_ops.create_buckets(nbuckets=2, users=users)
        pref_dir = {"prefix_dir": 'test_011'}
        run_io_sequentially(users=users, prefs=pref_dir)
        time.sleep(320)
        assert True, "msg"

    def test_02(self):
        time.sleep(30)
        assert False, "msg"

    def test_03(self):
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2)
        data = mgm_ops.create_buckets(nbuckets=2, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_03'}
        run_data_chk_obj.start_io(users=data, buckets=None, files_count=8, prefs=pref_dir)
        time.sleep(660)
        run_data_chk_obj.stop_io(users=data, di_check=True)
        assert True, "msg"

    def test_04(self):
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2)
        data = mgm_ops.create_buckets(nbuckets=2, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        run_data_chk_obj.start_io_async(
            users=data, buckets=None, files_count=3, prefs='test_04')
        time.sleep(320)
        run_data_chk_obj.stop_io_async(users=data, di_check=True)
        assert True, "msg"

    @pytest.mark.parametrize(
        "run_io_async", [{'user': 2, 'buckets': 5, 'files_count': 10, 'prefs': {'prefix_dir': 'test_05'}}],
        indirect=['run_io_async'])
    def test_05(self):
        time.sleep(320)
        assert True, "msg"
