from commons.utils import config_utils
from urllib.parse import quote_plus
from tools.rest_server import mongodbapi

cpath = "tools\\rest_server\\config.ini"
db_hostname = config_utils.get_config(cpath,"MongoDB","db_hostname")
db_name = config_utils.get_config(cpath,"MongoDB","db_name")
collection = config_utils.get_config(cpath,"MongoDB","collection")
collection = "r2_systems"
db_username = "dataread"
db_password = "seagate@123"
MONGODB_URI = "mongodb://{0}:{1}@{2}"

uri = MONGODB_URI.format(quote_plus(db_username),quote_plus(db_password), db_hostname)
mongodbapi.count_documents({},uri,db_name,collection)
