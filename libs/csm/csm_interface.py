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

"""This module implements CSM interface for CLI, GUI , REST"""

from libs.csm.rest.csm_rest_acc_capacity import AccountCapacity
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.csm.rest.csm_rest_audit_logs import RestAuditLogs
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_capacity import SystemCapacity
from libs.csm.rest.csm_rest_cluster import RestCsmCluster
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.csm.rest.csm_rest_stats import SystemStats
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.csm.rest.csm_rest_quota import GetSetQuota
from libs.csm.rest.csm_rest_information import RestInformation

class RESTInterface(AccountCapacity, SystemAlerts, RestAuditLogs, RestS3Bucket, SystemCapacity,
                    RestCsmCluster, RestCsmUser, RestIamUser, RestS3user, SystemStats, SystemHealth,
                    GetSetQuota, RestInformation):
    """
    Derived class all the rest api class in the lib dir. These has all the functionality available
    from csm libs.
    """

class CLIInterface:
    """
    Dummpy class for implementing CLI interface
    """

class GUIInterface:
    """
    Dummy class for implementing GUI interface
    """

def csm_api_factory(interface ="rest"):
    """
    Single point of access for all the tests and libs outside libs/csm for csm interface.
    """
    localizers = {"cli": CLIInterface, "rest": RESTInterface, "gui": GUIInterface,}
    return localizers[interface]()
