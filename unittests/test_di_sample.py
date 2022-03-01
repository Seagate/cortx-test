#
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
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
import time
import pytest
import logging
import multiprocessing
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

    def test_13(self):
        """
        Test verify start IO sleep for sometime and verify IO within test sequentially with and w/o
        future value to check upload started.
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=2, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_13'}

        future_obj = multiprocessing.Value('b', False)
        star_res = run_data_chk_obj.start_io(
            users=data, buckets=None, files_count=8, prefs=pref_dir, future_obj=future_obj)
        assert future_obj.value, "Upload failed"
        print(future_obj.value)
        assert star_res, "Upload failed"
        time.sleep(60)
        stop_res = run_data_chk_obj.stop_io(users=data, di_check=True)
        assert stop_res[0], "download failed"

        # Start IO without passing future class
        star_res = run_data_chk_obj.start_io(
            users=data, buckets=None, files_count=8, prefs=pref_dir)
        print(star_res)
        assert star_res, "Upload failed"
        time.sleep(60)
        stop_res = run_data_chk_obj.stop_io(users=data, di_check=True)
        assert stop_res[0], "download failed"

        assert True, "msg"

    def test_14(self):
        """
        Test start BG IO sleep for sometime and verify IO within test
        """
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=2, use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=2, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_14'}
        run_data_chk_obj.start_io_async(
            users=data, buckets=None, files_count=8, prefs=pref_dir)
        time.sleep(60)
        stop_res = run_data_chk_obj.stop_io_async(users=data, di_check=True)
        assert stop_res[0], "download failed"
        self.log.debug("Download: %s", stop_res)
        assert True, "msg"
