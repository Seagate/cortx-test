"""File consists constants to be used for generating random alerts."""
# dicts of type of alerts and alert setup functions
from aenum import Enum, NoAlias


class FaultAlerts(Enum, settings=NoAlias):
    """Enums for alert types."""
    CONTROLLER_FAULT = {'alert_type': 'enclosure',
                        'setup_function': 'enclosure_setup',
                        'resolve': 'CONTROLLER_FAULT_RESOLVED', 'support': 'HW'}
    CONTROLLER_A_FAULT = {'alert_type': 'enclosure',
                          'setup_function': 'enclosure_setup',
                          'resolve': 'CONTROLLER_A_FAULT_RESOLVED', 'support': 'HW'}
    CONTROLLER_B_FAULT = {'alert_type': 'enclosure',
                          'setup_function': 'enclosure_setup',
                          'resolve': 'CONTROLLER_B_FAULT_RESOLVED', 'support': 'HW'}
    PSU_FAULT = {'alert_type': 'enclosure', 'setup_function': 'enclosure_setup',
                 'resolve': 'PSU_FAULT_RESOLVED', 'support': 'HW'}
    DISK_DISABLE = {'alert_type': 'enclosure',
                    'setup_function': 'enclosure_setup',
                    'resolve': 'DISK_ENABLE', 'support': 'HW'}
    RAID_STOP_DEVICE_ALERT = {'alert_type': 'raid',
                              'setup_function': 'raid_setup',
                              'resolve': 'RAID_ASSEMBLE_DEVICE_ALERT',
                              'support': 'HW'}
    RAID_REMOVE_DISK_ALERT = {'alert_type': 'raid',
                              'setup_function': 'raid_setup',
                              'resolve': 'RAID_ADD_DISK_ALERT', 'support': 'HW'}
    DG_FAULT = {'alert_type': 'enclosure', 'setup_function': 'enclosure_setup',
                'resolve': 'DG_FAULT_RESOLVED', 'support': 'HW'}
    DISK_FAULT_NO_ALERT = {'alert_type': 'server_os',
                           'setup_function': 'server_setup', 'support': 'VM'}
    DISK_FAULT_ALERT = {'alert_type': 'server_os',
                        'setup_function': 'server_setup',
                        'resolve': 'DISK_FAULT_RESOLVED_ALERT', 'support': 'VM'}
    CPU_USAGE_NO_ALERT = {'alert_type': 'server_os',
                          'setup_function': 'server_setup', 'support': 'VM'}
    CPU_USAGE_ALERT = {'alert_type': 'server_os', 'setup_function': 'server_setup',
                       'resolve': 'CPU_USAGE_RESOLVED_ALERT', 'support': 'VM'}
    MEM_USAGE_NO_ALERT = {'alert_type': 'server_os',
                          'setup_function': 'server_setup', 'support': 'VM'}
    MEM_USAGE_ALERT = {'alert_type': 'server_os', 'setup_function': 'server_setup',
                       'resolve': 'MEM_USAGE_RESOLVED_ALERT', 'support': 'VM'}
    NW_PORT_FAULT = {'alert_type': 'server_fru',
                     'setup_function': 'server_fru_setup',
                     'resolve': 'NW_PORT_FAULT_RESOLVED', 'support': 'VM'}
