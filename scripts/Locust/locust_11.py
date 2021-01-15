# Put multiple same size objects in multiple buckets and
# get head object of multiple buckets simultaneously from multiple clients/workers


import os
from locust import HttpLocust, TaskSet, task
from random import randint
import time
from locust import events
import locust_utils


class MyTaskSet(TaskSet):
    def on_start(self):
        if os.path.exists(locust_utils.OBJ_NAME):
            try:
                os.remove(locust_utils.OBJ_NAME)
            except OSError:
                pass
        locust_utils.create_file()
        self.locust_params = locust_utils.start()

    def on_stop(self):
        locust_utils.stop()

    @task(3)
    def put_obj(self):
        for bucket in self.locust_params['bucket_list']:
            obj_name = "test_obj"+str(randint(0,100)) + str(time.time())
            print("Uploading object " + obj_name + " to bucket " + bucket)
            start_time = time.time()
            self.locust_params['s3_con'].upload_file(locust_utils.OBJ_NAME, bucket, obj_name)
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                    request_type="put",
                    name="upload_file",
                    response_time=total_time,
                    response_length=10,
                    )

    @task(3)
    def get_all_object_info(self):
        for bucket_name in self.locust_params['bucket_list']:
            bucket = self.locust_params['s3'].Bucket(bucket_name)
            objects = [obj.key for obj in bucket.objects.all()]
            for obj in objects:
                start_time = time.time()
                obj_sum = self.locust_params['s3'].meta.client.head_object(Bucket=bucket_name, Key=obj)
                print("Object Info --- {}".format(obj_sum))
                total_time = int((time.time() - start_time) * 1000)
                events.request_success.fire(
                        request_type="get",
                        name="head_object",
                        response_time=total_time,
                        response_length=10,
                        )


class MyLocust(HttpLocust):
    task_set = MyTaskSet
    min_wait = 5000
    max_wait = 15000
