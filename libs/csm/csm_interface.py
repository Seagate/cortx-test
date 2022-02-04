
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.csm.rest.csm_rest_s3user import RestS3user

class RESTInterface(RestCsmUser, RestIamUser, RestS3user):
    pass

class CLIInterface:
    pass

class GUIInterface:
    pass

def CSMFactory(interface ="rest"):
    localizers = {"cli": CLIInterface, "rest": RESTInterface, "gui": GUIInterface,}
    return localizers[interface]()