""" Module to test greenlet thread """
import unittest
import logging
from time import perf_counter
from commons.greenlet_worker import (GreenletThread, threads)
from commons.greenlet_worker import GeventPool

logger = logging.getLogger(__package__)
logger.setLevel(logging.DEBUG)


def fun(*args, **kwargs):
    """ function with args and kwargs"""
    print("Executing fun with->:")
    print("Arguments:{0} and Keyword Arguments {1} ", args, kwargs)
    return True


def fun1(x):
    """ function with single param return True"""
    print("Running fun1 Thread", x)
    return True


def fun2(y):
    """ function with single param returns False"""
    print("Running fun2 Thread", y)
    return False


class MyTestCase(unittest.TestCase):

    def test_1000_gthread(self):
        """Testing Greenlet Threading with passing function object or by overriding the _run if run=None """
        logger.info("Defining Number of Threads to be Started")
        number_of_threads = 100000
        logger.info("Creating GThread Objects and Executing")
        start = perf_counter()
        logger.info("StartTime is:%f", start)
        for i in range(number_of_threads):
            t_obj = GreenletThread(i, run=fun, x=1, y=2, z=3)
            t_obj.start()
            threads.append(t_obj)
        status, res = GreenletThread.terminate()
        logger.info(f"All Threads successfully Completed:{status} {res}")
        self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        logger.info("EndTime is:%f", end)
        logger.info("Total Time Taken with running threads: %f", (end - start))
        logger.info("-------------------------------------------------------------------------------------------------")

    def test_separate_gthread(self):
        """Testing Greenlet Threading with passing function object or by overriding the _run if run=None """
        logger.info("Defining Number of Threads to be Started")
        logger.info("Creating GThread Objects and Executing")
        start = perf_counter()
        logger.info("StartTime is:%f", start)
        t1_obj = GreenletThread(0, run=fun, x=1, y=2, z=3)
        t2_obj = GreenletThread("Running fun1", run=fun1)
        t3_obj = GreenletThread("Running Default")
        t1_obj.start()
        t2_obj.start()
        t3_obj.start()
        threads.append(t1_obj)
        threads.append(t2_obj)
        threads.append(t3_obj)
        status, res = GreenletThread.terminate()
        logger.info(f"All Threads successfully Completed:{status} {res}")
        self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        logger.info("EndTime is:%f", end)
        logger.info("Total Time Taken with running threads: %f", (end - start))
        logger.info("-------------------------------------------------------------------------------------------------")

    def test_1000_gpool(self):
        """Testing Greenlet Threading with passing function object or by overriding the _run if run=None """
        logger.info("Defining Number of Threads to be Started")
        number_of_threads = 100000
        logger.info("Creating GThread Objects and Executing")
        start = perf_counter()
        logger.info("StartTime is:%f", start)
        gp_obj = GeventPool(number_of_threads)
        for i in range(number_of_threads):
            gp_obj.add_handler(fun1, i)
        gp_obj.join_group()
        gp_obj.shutdown()
        logger.info(f"All Threads successfully Completed:")
        # self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        logger.info("EndTime is:%f", end)
        logger.info("Total Time Taken with running threads: %f", (end - start))
        logger.info("-------------------------------------------------------------------------------------------------")

    def test_gpool(self):
        """Testing Greenlet Threading with passing function object or by overriding the _run if run=None """
        logger.info("Defining Number of Threads to be Started")
        logger.info("Creating GThread Objects and Executing")
        start = perf_counter()
        logger.info("StartTime is:%f", start)
        gp_obj = GeventPool(3)
        gp_obj.add_handler(fun1, "First Method")
        gp_obj.add_handler(fun2, "Second Method")
        gp_obj.join_group()
        gp_obj.shutdown()
        logger.info(gp_obj.result())
        logger.info(f"All Threads successfully Completed:")
        # self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        logger.info("EndTime is:%f", end)
        logger.info("Total Time Taken with running threads: %f", (end - start))
        logger.info("-------------------------------------------------------------------------------------------------")


if __name__ == '__main__':
    unittest.main()
