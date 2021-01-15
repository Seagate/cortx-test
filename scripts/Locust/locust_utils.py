# Utility methods written for use accross all the locust test scenarios

import time
import os
import logging
import configparser
from random import randint
from botocore.client import Config
import boto3
from locust import events

logger = logging.getLogger(__name__)
config = configparser.ConfigParser()
config.read('/root/.aws/credentials')

ACCESS_KEY = config['locust']['aws_access_key_id']
SECRET_KEY = config['locust']['aws_secret_access_key']

locust_cfg = configparser.ConfigParser()
locust_cfg.read('scripts/Locust/locust_config.ini')

URL = locust_cfg['default']['host_url']
S3_CERT_PATH = locust_cfg['default']['S3_CERT_PATH']
IAM_CERT_PATH = locust_cfg['default']['IAM_CERT_PATH']
BUCKET_COUNT = int(locust_cfg['default']['BUCKET_COUNT'])  # Buckets per user
OBJ_NAME = locust_cfg['default']['OBJ_NAME']
GET_OBJ_PATH = locust_cfg['default']['GET_OBJ_PATH']
locust_var = dict()
locust_var['bucket_list'] = []
MAX_POOL_CONNECTIONS = int(os.getenv('MAX_POOL_CONNECTIONS', locust_cfg['default']['MAX_POOL_CONNECTIONS']))
logger.info("Max_Pool_Connections: {}".format(MAX_POOL_CONNECTIONS))


def create_file(min_size, max_size):
    """
    Creates file of random size from the given range
    :param str min_size: minimum file size
    :param str max_size: maximum file size
    """
    with open(OBJ_NAME, 'wb') as fout:
        fout.write(os.urandom(randint(1024 * min_size, 1024 * max_size)))


def start():
    session = boto3.session.Session()
    locust_var['s3_con'] = session.client(
        service_name="s3",
        verify=S3_CERT_PATH,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        endpoint_url=URL,
        config=Config(max_pool_connections=MAX_POOL_CONNECTIONS)
    )
    locust_var['s3'] = session.resource(
        service_name="s3",
        verify=S3_CERT_PATH,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        endpoint_url=URL,
        config=Config(max_pool_connections=MAX_POOL_CONNECTIONS)
    )
    for i in range(BUCKET_COUNT):
        bucket_name = "testbucket{}".format(str(time.time()))
        start_time = time.time()
        logger.info("Creating bucket: {}".format(bucket_name))
        locust_var['s3_con'].create_bucket(Bucket=bucket_name)
        locust_var['bucket_list'].append(bucket_name)
        total_time = int((time.time() - start_time) * 1000)
        events.request_success.fire(
            request_type="put",
            name="create_bucket",
            response_time=total_time,
            response_length=10,
        )
    logger.info("Buckets Created: {}".format(locust_var['bucket_list']))
    return locust_var


def stop():
    logger.info("Bucket list: {}".format(locust_var['bucket_list']))
    for bucket in locust_var['bucket_list']:
        bucket = locust_var['s3'].Bucket(bucket)
        bucket.objects.all().delete()
        start_time = time.time()
        bucket.delete()
        logger.info("Deleted bucket : {}".format(bucket))
        total_time = int((time.time() - start_time) * 1000)
        events.request_success.fire(
            request_type="delete",
            name="delete_bucket",
            response_time=total_time,
            response_length=10,
        )
        try:
            os.remove(OBJ_NAME)
        except OSError:
            pass
        try:
            os.remove(GET_OBJ_PATH)
        except OSError:
            pass
