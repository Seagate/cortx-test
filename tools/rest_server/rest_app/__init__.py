from flask_restx import Api
from .test_execution_api import api as te_apis
from .cmi_api import api as cmi_apis
from .systems_api import api as systems_apis
from .timings_api import api as timings_apis

api = Api(title="MongoDB APIs", version="1.0", description="APIs for accessing MongoDB")

api.add_namespace(te_apis)
api.add_namespace(cmi_apis)
api.add_namespace(systems_apis)
api.add_namespace(timings_apis)
