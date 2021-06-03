"""File consists constants to be used for alert simulator."""
# dicts of default values for input_parameters
PSU_FAULT = {"enclid": 0, "pos": "left", "fru": "psu",
             "type_fault": "e", "ctrl_name": "a"}
PSU_FAULT_RESOLVED = {"enclid": 0, "pos": "left", "fru": "psu",
                      "type_fault": "r", "ctrl_name": "a"}
CONTROLLER_FAULT = {"enclid": 0, "pos": "a", "fru": "ctrl",
                    "type_fault": "e", "ctrl_name": "a"}
CONTROLLER_FAULT_RESOLVED = {"enclid": 0, "pos": "a", "fru": "ctrl",
                             "type_fault": "r", "ctrl_name": "a"}
CONTROLLER_A_FAULT = {'enclid': 0, 'pos': 'a', 'fru': 'ctrl',
                      'type_fault': 'e', 'ctrl_name': 'both'}
CONTROLLER_A_FAULT_RESOLVED = {'enclid': 0, 'pos': 'a', 'fru': 'ctrl',
                               'type_fault': 'r', 'ctrl_name': 'both'}
CONTROLLER_B_FAULT = {'enclid': 0, 'pos': 'b', 'fru': 'ctrl',
                      'type_fault': 'e', 'ctrl_name': 'both'}
CONTROLLER_B_FAULT_RESOLVED = {'enclid': 0, 'pos': 'b', 'fru': 'ctrl',
                               'type_fault': 'r', 'ctrl_name': 'both'}

DISK_DISABLE = {"enclid": 0, "ctrl_name": "A", "phy_num": 5,
                "operation": "Disabled", "exp_status": ["Degraded", "Fault"],
                "telnet_file": "/root/telnet.xml"}
DISK_ENABLE = {"enclid": 0, "ctrl_name": "A", "phy_num": 5,
               "operation": "Enabled", "exp_status": "OK",
               "telnet_file": "/root/telnet.xml"}
DISK_FAULT_NO_ALERT = {"du_val": 8, "fault": False, "fault_resolved": False}
DISK_FAULT_ALERT = {"du_val": 8, "fault": True, "fault_resolved": False}
DISK_FAULT_RESOLVED_ALERT = {"du_val": 8, "fault": True, "fault_resolved": True}
CPU_USAGE_NO_ALERT = {"delta_cpu_usage": 0.3}
CPU_USAGE_ALERT = {"delta_cpu_usage": -0.3}
CPU_USAGE_RESOLVED_ALERT = {"delta_cpu_usage": 0}
MEM_USAGE_NO_ALERT = {"delta_mem_usage": 3}
MEM_USAGE_ALERT = {"delta_mem_usage": -3}
MEM_USAGE_RESOLVED_ALERT = {"delta_mem_usage": 0}
RAID_ASSEMBLE_DEVICE_ALERT = {"operation": "assemble", "md_device": None,
                              "disk": None}
RAID_STOP_DEVICE_ALERT = {"operation": "stop", "md_device": None,
                          "disk": None}
RAID_FAIL_DISK_ALERT = {"operation": "fail_disk", "md_device": None,
                        "disk": None}
RAID_REMOVE_DISK_ALERT = {"operation": "remove_disk", "md_device": None,
                          "disk": None}
RAID_ADD_DISK_ALERT = {"operation": "add_disk", "md_device": None, "disk": None}
IEM_TEST_ERROR_ALERT = {"cmd": 'logger -i -p local3.err '
                               'IEC: EO0090090900:Test IEM'}
DG_FAULT = {"enclid": 0, "ctrl_name": ['A', 'B'], "operation": "Disabled",
            "disk_group": "dg00"}
DG_FAULT_RESOLVED = {"enclid": 0, "ctrl_name": ["A", "B"],
                     "operation": "Enabled", "disk_group": "dg00",
                     "phy_num": ["0.0", "0.2"], "poll": True}
