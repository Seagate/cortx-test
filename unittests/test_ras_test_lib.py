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
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Unittests for ras test lib
"""
import pytest
from libs.ras.ras_test_lib import RASTestLib

FIRST_NODE_TEST_OBJ = RASTestLib(host="sm7-r19.pun.seagate.com")
SECOND_NODE_TEST_OBJ = RASTestLib(host="sm8-r19.pun.seagate.com")


@pytest.mark.skip
@pytest.mark.parametrize(
    "exchange, key, expected", [('sspl-out', 'sensor-key', True), ('sspl-out', 'sensor-key', False)])
def test_start_rabbitmq_reader_cmd(exchange, key, expected):
    res = FIRST_NODE_TEST_OBJ.start_rabbitmq_reader_cmd(exchange, key)
    # needs cleanup calls
    assert res == expected


@pytest.mark.skip
def test_check_sspl_event_generated():
    res = FIRST_NODE_TEST_OBJ.check_sspl_event_generated()
    assert res[0]


@pytest.mark.skip
def test_check_status_file():
    res = FIRST_NODE_TEST_OBJ.check_status_file()
    assert res[0]


@pytest.mark.skip
def test_put_kv_store():
    res = FIRST_NODE_TEST_OBJ.put_kv_store()
    assert res


@pytest.mark.skip
@pytest.mark.parametrize(
    "path, restore, expected", [('/tmp/sspl.conf', True, True), ('', True, None)])
def test_retain_config(path, restore, expected):
    path = "/tmp/sspl.conf"
    res = FIRST_NODE_TEST_OBJ.retain_config(path, restore=True)
    assert res


@pytest.mark.skip
def test_validate_alert_log():
    res = FIRST_NODE_TEST_OBJ.validate_alert_log("/root/extracted_alert.log", )
    assert res


@pytest.mark.skip
def test_update_threshold_values():
    res = FIRST_NODE_TEST_OBJ.update_threshold_values()
    assert res


@pytest.mark.skip
def test_reset_log_file():
    res = FIRST_NODE_TEST_OBJ.reset_log_file()
    assert res


@pytest.mark.skip
def test_get_sspl_state():
    res = FIRST_NODE_TEST_OBJ.get_sspl_state()
    assert res


@pytest.mark.skip
def test_generate_disk_full_alert():
    res = FIRST_NODE_TEST_OBJ.generate_disk_full_alert()
    assert res


@pytest.mark.skip
def test_list_alert_validation():
    res = FIRST_NODE_TEST_OBJ.list_alert_validation()
    assert res[0]


@pytest.mark.skip
def test_generate_cpu_usage_alert():
    res = FIRST_NODE_TEST_OBJ.generate_cpu_usage_alert()
    assert res[0]


@pytest.mark.skip
def test_generate_memory_usage_alert():
    res = FIRST_NODE_TEST_OBJ.generate_memory_usage_alert()
    assert res


@pytest.mark.skip
def test_update_mdadm_config():
    res = FIRST_NODE_TEST_OBJ.update_mdadm_config()
    assert str() == type(res)


@pytest.mark.skip
def test_create_mdraid_disk_array():
    res = FIRST_NODE_TEST_OBJ.create_mdraid_disk_array()
    assert res


@pytest.mark.skip
def test_assemble_mdraid_device():
    res = FIRST_NODE_TEST_OBJ.assemble_mdraid_device()
    assert res


@pytest.mark.skip
def test_stop_mdraid_device():
    res = FIRST_NODE_TEST_OBJ.stop_mdraid_device()
    assert res


@pytest.mark.skip
def test_fail_disk_mdraid():
    res = FIRST_NODE_TEST_OBJ.fail_disk_mdraid()
    assert res


@pytest.mark.skip
def test_remove_faulty_disk():
    res = FIRST_NODE_TEST_OBJ.remove_faulty_disk()
    assert res


@pytest.mark.skip
def test_add_disk_mdraid():
    res = FIRST_NODE_TEST_OBJ.add_disk_mdraid()
    assert res


@pytest.mark.skip
def test_remove_mdraid_disk_array():
    res = FIRST_NODE_TEST_OBJ.remove_mdraid_disk_array(md_device=None)
    assert res


def test_get_sspl_state_pcs():
    res = FIRST_NODE_TEST_OBJ.get_sspl_state_pcs()
    print(res)
    assert dict == type(res)
