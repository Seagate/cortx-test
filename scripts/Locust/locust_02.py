##Create multiple buckets and delete created buckets simultaneously from multiple clients/workers

import os
import time
import boto3
import random
from locust import HttpLocust, TaskSet, task
from random import randint
from locust import events
import locust_utils



class MyTaskSet(TaskSet):
    def on_start(self):
        session = boto3.session.Session()
        locust_utils.locust_var['s3_con'] = session.client(
              service_name="s3",
              verify=locust_utils.s3_cert_path,
              aws_access_key_id=locust_utils.ACCESS_KEY,
              aws_secret_access_key=locust_utils.SECRET_KEY,
              endpoint_url=locust_utils.URL
        )       
        locust_utils.locust_var['s3'] = session.resource(
              service_name="s3",
              verify=locust_utils.s3_cert_path,
              aws_access_key_id=locust_utils.ACCESS_KEY,
              aws_secret_access_key=locust_utils.SECRET_KEY,
              endpoint_url=locust_utils.URL
        )
        locust_utils.locust_var['bucket_list'] = []


    @task(2)
    def create_multiple_buckets(self):
        print("Creating Buckets")
        bucket_name = "testbucket" + str(randint(0, 100)) + str(time.time())
        start_time = time.time()
        locust_utils.locust_var['s3_con'].create_bucket(Bucket=bucket_name)
        locust_utils.locust_var['bucket_list'].append(bucket_name)
        total_time = int((time.time() - start_time) * 1000)
        events.request_success.fire(
                request_type="put",
                name="create_bucket",
                response_time=total_time,
                response_length=10,
                )
        print("Bucket Created : {}".format(bucket_name))


    @task(1)
    def delete_multiple_buckets(self):
        if len(locust_utils.locust_var['bucket_list']) > 1:
            bucket_name = random.choice(locust_utils.locust_var['bucket_list'])
            start_time = time.time()
            print("Deleting Buckets")
            bucket = locust_utils.locust_var['s3'].Bucket(bucket_name)
            bucket.delete()
            print("Deleted Bucket :", bucket)
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                request_type="delete",
                name="delete_bucket",
                response_time=total_time,
                response_length=10,
                )
        

    def on_stop(self):
        locust_utils.stop()
    

class MyLocust(HttpLocust):
    task_set = MyTaskSet
    min_wait = 5000
    max_wait = 15000
