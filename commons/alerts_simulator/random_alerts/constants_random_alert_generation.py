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
#"""File consists constants to be used for generating random alerts."""
# dicts of type of alerts and alert setup functions
from aenum import Enum, NoAlias


class FaultAlerts(Enum, settings=NoAlias):
    """Enums for alert types."""
    CONTROLLER_FAULT = {'alert_type': 'enclosure',
                        'function': 'enclosure_fun',
                        'resolve': 'CONTROLLER_FAULT_RESOLVED', 'support': 'HW'}
    CONTROLLER_A_FAULT = {'alert_type': 'enclosure',
                          'function': 'enclosure_fun',
                          'resolve': 'CONTROLLER_A_FAULT_RESOLVED', 'support': 'HW'}
    CONTROLLER_B_FAULT = {'alert_type': 'enclosure',
                          'function': 'enclosure_fun',
                          'resolve': 'CONTROLLER_B_FAULT_RESOLVED', 'support': 'HW'}
    PSU_FAULT = {'alert_type': 'enclosure', 'function': 'enclosure_fun',
                 'resolve': 'PSU_FAULT_RESOLVED', 'support': 'HW'}
    DISK_DISABLE = {'alert_type': 'enclosure',
                    'function': 'enclosure_fun',
                    'resolve': 'DISK_ENABLE', 'support': 'HW'}
    RAID_STOP_DEVICE_ALERT = {'alert_type': 'raid',
                              'function': 'raid_fun',
                              'resolve': 'RAID_ASSEMBLE_DEVICE_ALERT',
                              'support': 'HW'}
    RAID_REMOVE_DISK_ALERT = {'alert_type': 'raid',
                              'function': 'raid_fun',
                              'resolve': 'RAID_ADD_DISK_ALERT', 'support': 'HW'}
    DG_FAULT = {'alert_type': 'enclosure', 'function': 'enclosure_fun',
                'resolve': 'DG_FAULT_RESOLVED', 'support': 'HW'}
    DISK_FAULT_NO_ALERT = {'alert_type': 'server_os',
                           'function': 'server_fun', 'support': 'VM'}
    DISK_FAULT_ALERT = {'alert_type': 'server_os',
                        'function': 'server_fun',
                        'resolve': 'DISK_FAULT_RESOLVED_ALERT', 'support': 'VM'}
    CPU_USAGE_NO_ALERT = {'alert_type': 'server_os',
                          'function': 'server_fun', 'support': 'VM'}
    CPU_USAGE_ALERT = {'alert_type': 'server_os', 'function': 'server_fun',
                       'resolve': 'CPU_USAGE_RESOLVED_ALERT', 'support': 'VM'}
    MEM_USAGE_NO_ALERT = {'alert_type': 'server_os',
                          'function': 'server_fun', 'support': 'VM'}
    MEM_USAGE_ALERT = {'alert_type': 'server_os', 'function': 'server_fun',
                       'resolve': 'MEM_USAGE_RESOLVED_ALERT', 'support': 'VM'}
    NW_PORT_FAULT = {'alert_type': 'server_fru',
                     'function': 'server_fru_fun',
                     'resolve': 'NW_PORT_FAULT_RESOLVED', 'support': 'VM'}
