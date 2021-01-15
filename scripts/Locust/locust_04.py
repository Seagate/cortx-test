#Put multiple same size objects in single bucket and get object count of that bucket simultaneously from multiple clients/workers

import os
import time
import boto3
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
        print("Creating a bucket")
        global bucket_name
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
        print("Bucket Created :", bucket_name)
        locust_utils.create_file() 
    
    @task(3)
    def put_obj(self):
        obj_name = "test_obj"+str(randint(0,100)) + str(time.time())
        print("Uploading object " + obj_name + " to bucket " + bucket_name)
        start_time = time.time()
        locust_utils.locust_var['s3_con'].upload_file(locust_utils.OBJ_NAME, bucket_name, obj_name)
        total_time = int((time.time() - start_time) * 1000)
        events.request_success.fire(
                request_type="put",
                name="upload_file",
                response_time=total_time,
                response_length=10,
                )

    @task(1)
    def get_all_objects(self):
        bucket = []
        start_time = time.time()
        bucket = locust_utils.locust_var['s3_con'].list_objects(Bucket=str(bucket_name))['Contents']
        size = len(bucket)
        print("Bucket " + bucket_name + " object count : ", size)
        total_time = int((time.time() - start_time) * 1000)
        events.request_success.fire(
                    request_type="get",
                    name="get_all_obj_count",
                    response_time=total_time,
                    response_length=10,
                    )    


    def on_stop(self):
        locust_utils.stop()
    

class MyLocust(HttpLocust):
    task_set = MyTaskSet
    min_wait = 5000
    max_wait = 15000
