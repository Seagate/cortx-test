# Put multiple different size objects in multiple buckets and
# download objects simultaneously from multiple clients/workers
# delete random objects from all created buckets

import os
import logging
from random import randint
import random
import time
from locust import HttpLocust, TaskSet, task
from locust import events
import locust_utils

logger = logging.getLogger(__name__)
min_obj_size = int(os.getenv("MIN_SIZE", 5))
max_obj_size = int(os.getenv("MAX_SIZE", 50))
logger.info("Minimum Object Size: {} KB".format(min_obj_size))
logger.info("Maximum Object Size: {} KB".format(max_obj_size))


class MyTaskSet(TaskSet):
    def on_start(self):
        self.locust_params = locust_utils.start()

    def teardown(self):
        locust_utils.stop()

    @task(3)
    def put_obj(self):
        for bucket in self.locust_params['bucket_list']:
            if os.path.exists(locust_utils.OBJ_NAME):
                try:
                    os.remove(locust_utils.OBJ_NAME)
                except OSError:
                    pass
            locust_utils.create_file(min_obj_size, max_obj_size)
            obj_name = "test_obj{0}{1}".format(str(randint(0, 100)), str(time.time()))
            logger.info("Uploading object {0} into bucket {1}".format(obj_name, bucket))
            start_time = time.time()
            self.locust_params['s3_con'].upload_file(locust_utils.OBJ_NAME, bucket, obj_name)
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                    request_type="put",
                    name="upload_file",
                    response_time=total_time,
                    response_length=10,
                    )

    @task(1)
    def download_object(self):
        for bucket_name in self.locust_params['bucket_list']:
            bucket = self.locust_params['s3'].Bucket(bucket_name)
            objects = [obj.key for obj in bucket.objects.all()]
            if len(objects) > 1:
                start_time = time.time()
                if os.path.exists(locust_utils.GET_OBJ_PATH):
                    try:
                        os.remove(locust_utils.GET_OBJ_PATH)
                    except OSError:
                        pass
                logger.info("Starting downloading the object")
                obj_name = random.choice(objects)
                self.locust_params['s3'].Bucket(bucket_name).download_file(obj_name, locust_utils.GET_OBJ_PATH)
                logger.info("The {} has been downloaded successfully at mentioned "
                      "filepath {}".format(obj_name, locust_utils.GET_OBJ_PATH))
                total_time = int((time.time() - start_time) * 1000)
                events.request_success.fire(
                    request_type="get",
                    name="download_object",
                    response_time=total_time,
                    response_length=10,
                )

    @task(1)
    def delete_object(self):
        for bucket_name in self.locust_params['bucket_list']:
            bucket = self.locust_params['s3'].Bucket(bucket_name)
            objects = [obj.key for obj in bucket.objects.all()]
            if len(objects) > 1:
                start_time = time.time()
                obj_name = random.choice(objects)
                logger.info("Deleting object {0} from the bucket {1}".format(obj_name, bucket_name))
                self.locust_params['s3'].Object(bucket_name, obj_name).delete()
                total_time = int((time.time() - start_time) * 1000)
                events.request_success.fire(
                    request_type="delete",
                    name="delete_object",
                    response_time=total_time,
                    response_length=10,
                )


class MyLocust(HttpLocust):
    task_set = MyTaskSet
    min_wait = 5000
    max_wait = 15000
