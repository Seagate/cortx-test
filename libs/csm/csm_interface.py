

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
    pass

class CLIInterface:
    pass

class GUIInterface:
    pass

def CSMFactory(interface ="rest"):
    localizers = {"cli": CLIInterface, "rest": RESTInterface, "gui": GUIInterface,}
    return localizers[interface]()