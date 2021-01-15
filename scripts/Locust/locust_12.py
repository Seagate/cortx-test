# Create multiple buckets and get head bucket simultaneously from multiple clients/workers


from locust import HttpLocust, TaskSet, task
from random import randint
import random
import time
from locust import events
import locust_utils


class MyTaskSet(TaskSet):
    def on_start(self):
        self.locust_params = locust_utils.start()

    def on_stop(self):
        locust_utils.stop()

    @task(3)
    def create_bucket(self):
        start_time = time.time()
        bucket_name = "testbucket" + str(randint(0, 100)) + str(time.time())
        print("Creating Bucket")
        bucket = self.locust_params['s3'].create_bucket(Bucket=bucket_name)
        print("Bucket Created {}".format(bucket))
        self.locust_params['bucket_list'].append(bucket_name)
        total_time = int((time.time() - start_time) * 1000)
        events.request_success.fire(
                request_type="put",
                name="create_bucket",
                response_time=total_time,
                response_length=10,
                )

    @task(3)
    def get_head_bucket(self):
        if len(self.locust_params['bucket_list']) > 1:
            bucket_name = random.choice(self.locust_params['bucket_list'])
            start_time = time.time()
            print("Listing head bucket")
            bucket = self.locust_params['s3'].meta.client.head_bucket(Bucket=bucket_name)
            print(bucket)
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                    request_type="get",
                    name="get_head_bucket",
                    response_time=total_time,
                    response_length=10,
                    )


class MyLocust(HttpLocust):
    task_set = MyTaskSet
    min_wait = 5000
    max_wait = 15000
