#Create multiple already existing buckets simultaneously from multiple clients/workers


from locust import HttpLocust, TaskSet, task
from random import randint
from locust import events
import os
import time
import locust_utils
import boto3


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

    @task(1)
    def create_multiple_buckets(self):
        for i in range(locust_utils.BUCKET_COUNT):
            print("Creating bucket")
            bucket_name = "testbucket"
            start_time = time.time()
            locust_utils.locust_var['s3_con'].create_bucket(Bucket=bucket_name + str(i))
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                     request_type="put",
                     name="create_multiple_buckets",
                     response_time=total_time,
                     response_length=10,
                         )  

    @task(1)
    def create_existing_multiple_buckets(self):
        for i in range(locust_utils.BUCKET_COUNT):
            print("Creating bucket")
            bucket_name = "testbucket"
            start_time = time.time()
            # locust_utils.locust_var['s3_con'].create_bucket(Bucket=bucket_name + str(i))
            locust_utils.locust_var['s3_con'].create_bucket(Bucket=bucket_name + str(i))
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                     request_type="put",
                     name="create_existing_multiple_buckets",
                     response_time=total_time,
                     response_length=10,
                         )
    def on_stop(self):
        locust_utils.stop()

class MyLocust(HttpLocust):
    task_set = MyTaskSet
    min_wait = 5000
    max_wait = 15000
