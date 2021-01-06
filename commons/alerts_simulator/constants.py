# dicts of default values for input_parameters
psu_fault = {"enclid": 0, "pos": "left", "fru": "psu",
             "type_fault": "e", "ctrl_name": "a"}
psu_fault_resolved = {"enclid": 0, "pos": "left", "fru": "psu",
                      "type_fault": "r", "ctrl_name": "a"}
controller_fault = {"enclid": 0, "pos": "a", "fru": "ctrl",
                    "type_fault": "e", "ctrl_name": "a"}
controller_fault_resolved = {"enclid": 0, "pos": "a", "fru": "ctrl",
                             "type_fault": "r", "ctrl_name": "a"}
controller_a_fault = {'enclid': 0, 'pos': 'a', 'fru': 'ctrl', 'type_fault': 'e', 'ctrl_name': 'both'}
controller_a_fault_resolved = {'enclid': 0, 'pos': 'a', 'fru': 'ctrl', 'type_fault': 'r', 'ctrl_name': 'both'}
controller_b_fault = {'enclid': 0, 'pos': 'b', 'fru': 'ctrl', 'type_fault': 'e', 'ctrl_name': 'both'}
controller_b_fault_resolved = {'enclid': 0, 'pos': 'b', 'fru': 'ctrl', 'type_fault': 'r', 'ctrl_name': 'both'}

disk_disable = {"enclid": 0, "ctrl_name": "A", "phy_num": 5,
                "operation": "Disabled", "exp_status": ["Degraded", "Fault"],
                "telnet_file": "/root/telnet.xml"}
disk_enable = {"enclid": 0, "ctrl_name": "A", "phy_num": 5,
               "operation": "Enabled", "exp_status": "OK",
               "telnet_file": "/root/telnet.xml"}
disk_fault_no_alert = {"du_val": 1, "fault": False, "fault_resolved": False}
disk_fault_alert = {"du_val": 1, "fault": True, "fault_resolved": False}
disk_fault_resolved_alert = {"du_val": 1, "fault": True, "fault_resolved": True}
cpu_usage_no_alert = {"delta_cpu_usage": 0.3}
cpu_usage_alert = {"delta_cpu_usage": -0.3}
cpu_usage_resolved_alert = {"delta_cpu_usage": 0}
mem_usage_no_alert = {"delta_mem_usage": 3}
mem_usage_alert = {"delta_mem_usage": -3}
mem_usage_resolved_alert = {"delta_mem_usage": 0}
raid_assemble_device_alert = {"operation": "assemble", "md_device": None, "disk": None}
raid_stop_device_alert = {"operation": "stop", "md_device": None, "disk": None}
raid_fail_disk_alert = {"operation": "fail_disk", "md_device": None, "disk": None}
raid_remove_disk_alert = {"operation": "remove_disk", "md_device": None, "disk": None}
raid_add_disk_alert = {"operation": "add_disk", "md_device": None, "disk": None}
iem_test_error_alert = {"cmd":'logger -i -p local3.err IEC: EO0090090900:Test IEM'}