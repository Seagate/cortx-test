import os
import pytest
from libs.ras.ras_test_lib import RASTestLib

First_Node_TEST_OBJ = RASTestLib(host="sm7-r19.pun.seagate.com")
Second_Node_TEST_OBJ = RASTestLib(host="sm8-r19.pun.seagate.com")


@pytest.mark.skip
@pytest.mark.parametrize(
    "exchange, key, expected", [('sspl-out', 'sensor-key', True), ('sspl-out', 'sensor-key', False)])
def test_start_rabbitmq_reader_cmd(exchange, key, expected):
    res = First_Node_TEST_OBJ.start_rabbitmq_reader_cmd(exchange, key)
    # needs cleanup calls
    assert res[0] == expected


@pytest.mark.skip
def test_check_sspl_event_generated():
    res = First_Node_TEST_OBJ.check_sspl_event_generated()
    assert res[0]


@pytest.mark.skip
def test_check_status_file():
    res = First_Node_TEST_OBJ.check_status_file()
    assert res[0]


@pytest.mark.skip
def test_put_kv_store():
    res = First_Node_TEST_OBJ.put_kv_store()
    assert res


@pytest.mark.skip
@pytest.mark.parametrize(
    "path, restore, expected", [('/tmp/sspl.conf', True, True), ('', True, None)])
def test_retain_config(path, restore, expected):
    path = "/tmp/sspl.conf"
    res = First_Node_TEST_OBJ.retain_config(path, restore=True)
    assert res


@pytest.mark.skip
def test_validate_alert_log():
    res = First_Node_TEST_OBJ.validate_alert_log("/root/extracted_alert.log", )
    assert res


@pytest.mark.skip
def test_update_threshold_values():
    res = First_Node_TEST_OBJ.update_threshold_values()
    assert res


@pytest.mark.skip
def test_reset_log_file():
    res = First_Node_TEST_OBJ.reset_log_file()
    assert res


@pytest.mark.skip
def test_get_sspl_state():
    res = First_Node_TEST_OBJ.get_sspl_state()
    assert res


@pytest.mark.skip
def test_generate_disk_full_alert():
    res = First_Node_TEST_OBJ.generate_disk_full_alert()
    assert res


@pytest.mark.skip
def test_list_alert_validation():
    res = First_Node_TEST_OBJ.list_alert_validation()
    assert res[0]


@pytest.mark.skip
def test_generate_cpu_usage_alert():
    res = First_Node_TEST_OBJ.generate_cpu_usage_alert()
    assert res[0]


@pytest.mark.skip
def test_generate_memory_usage_alert():
    res = First_Node_TEST_OBJ.generate_memory_usage_alert()
    assert res


@pytest.mark.skip
def test_update_mdadm_config():
    res = First_Node_TEST_OBJ.update_mdadm_config()
    assert str() == type(res)


@pytest.mark.skip
def test_create_mdraid_disk_array():
    res = First_Node_TEST_OBJ.create_mdraid_disk_array()
    assert res


@pytest.mark.skip
def test_assemble_mdraid_device():
    res = First_Node_TEST_OBJ.assemble_mdraid_device()
    assert res


@pytest.mark.skip
def test_stop_mdraid_device():
    res = First_Node_TEST_OBJ.stop_mdraid_device()
    assert res


@pytest.mark.skip
def test_fail_disk_mdraid():
    res = First_Node_TEST_OBJ.fail_disk_mdraid()
    assert res


@pytest.mark.skip
def test_remove_faulty_disk():
    res = First_Node_TEST_OBJ.remove_faulty_disk()
    assert res


@pytest.mark.skip
def test_add_disk_mdraid():
    res = First_Node_TEST_OBJ.add_disk_mdraid()
    assert res


@pytest.mark.skip
def test_remove_mdraid_disk_array():
    res = First_Node_TEST_OBJ.remove_mdraid_disk_array(md_device=None)
    assert res


def test_get_sspl_state_pcs():
    res = First_Node_TEST_OBJ.get_sspl_state_pcs()
    assert dict == type(res)
