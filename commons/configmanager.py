import yaml
import logging
from urllib.parse import quote_plus
from pymongo import MongoClient
from commons.utils import config_utils
from commons import pswdmanager
#from config.params import DB_CONFIG, MONGODB_URI

LOG = logging.getLogger(__name__)
DB_CONFIG = "tools\\rest_server\\config.ini"

def get_config_yaml(fpath: str) -> dict:
    """Reads the config and decrypts the passwords

    :param fpath: configuration file path
    :return [type]: dictionary containing config data
    """
    with open(fpath) as fin:
        LOG.debug("Reading details from file : %s",fpath)
        data = yaml.safe_load(fin)
        data['end'] = 'end'
        LOG.debug("Decrypting password from file : %s",fpath)
        pswdmanager.decrypt_all_passwd(data)
    return data


def get_config_db(setup_query:dict, drop_id = True):
    """Reads the configuration from the database

    :param setup_query:collection which will be read eg: {"setupname":"automation"}
    """
    sys_coll = _get_collection_obj()
    LOG.debug("Finding the setup details: %s",setup_query)
    cursor = sys_coll.find(setup_query)
    docs={}
    for doc in cursor:
        if drop_id:
            LOG.debug("IDs fields from MongoDB will be dropped")
            doc.pop('_id')
        if "setupname" in doc.keys():
            LOG.debug("Reading the -- %s --setup details",doc['setupname'])
            docs.update({doc['setupname']:doc})
    return docs

def _get_collection_obj():
    db_hostname = config_utils.get_config(DB_CONFIG,"MongoDB","db_hostname")
    LOG.debug("Database hostname: %s", db_hostname)
    db_name = config_utils.get_config(DB_CONFIG,"MongoDB","db_name")
    LOG.debug("Database name: %s", db_name)
    collection = config_utils.get_config(DB_CONFIG,"MongoDB","system_info_collection")
    LOG.debug("Collection name: %s", collection)
    db_creds = pswdmanager.get_secrets(secret_ids=['DBUSER', 'DBPSWD'])
    mongodburi = "mongodb://{0}:{1}@{2}"
    uri = mongodburi.format(quote_plus(db_creds['DBUSER']),quote_plus(db_creds['DBPSWD']), db_hostname)
    client = MongoClient(uri)
    setup_db = client[db_name]
    collection_obj = setup_db[collection]
    LOG.debug("Collection obj for DB interaction %s",collection_obj)
    return collection_obj

def update_config_db(setup_query:dict, data:dict)->dict:
    """update the setup details in the database

    :param setup_query: Query for setup eg: {"setupname":"automation"}
    :return [type]:
    """
    sys_coll = _get_collection_obj()
    LOG.debug("Setup query : %s",setup_query)
    LOG.debug("Data to be updated : %s",data)
    rdata = sys_coll.update_many(setup_query, data)
    LOG.debug("Data is updated successfully")
    return rdata

def get_config_wrapper(**kwargs):
    """Get the configuration from the database as well as yaml and merge.
    It is expected that duplicate data should not be present between DB and yaml
    """
    flag = False
    data = {}
    if "fpath" in kwargs:
        flag = True
        LOG.debug("Reading config from yaml file: %s", kwargs['fpath'])
        data.update(get_config_yaml(fpath=kwargs['fpath']))
    if "setup_query" in kwargs:
        flag = True
        LOG.debug("Reading config from DB for setup: %s", kwargs['setup_query'])
        data.update(get_config_db(setup_query=kwargs['setup_query']))
    if not flag:
        LOG.error("Invalid keyword argument")
        raise ValueError("Invalid argument")
    return data
