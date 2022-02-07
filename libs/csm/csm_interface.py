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


class RESTInterface(AccountCapacity, SystemAlerts, RestAuditLogs, RestS3Bucket, SystemCapacity,
                    RestCsmCluster, RestCsmUser, RestIamUser, RestS3user, SystemStats, SystemHealth
                    ):
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
