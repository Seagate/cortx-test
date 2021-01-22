"""Module to test greenlet thread"""
import unittest
import logging
from time import perf_counter
from commons.greenlet_worker import (GreenletThread, THREADS)
from commons.greenlet_worker import GeventPool

LOGGER = logging.getLogger(__package__)
LOGGER.setLevel(logging.DEBUG)


def fun(*args, **kwargs):
    """function with args and kwargs"""
    print("Executing fun with->:")
    print("Arguments:{0} and Keyword Arguments {1} ", args, kwargs)
    return True


def fun1(x_arg):
    """function with single param return True"""
    print("Running fun1 Thread", x_arg)
    return True


def fun2(y_arg):
    """function with single param returns False"""
    print("Running fun2 Thread", y_arg)
    return False


class GEventTestCase(unittest.TestCase):
    """Testing gevent threads"""

    def test_1000_gthread(self):
        """
        Testing Greenlet Threading with passing function object or by overriding the _run
        if run=None.
        """
        LOGGER.info("Defining Number of Threads to be Started")
        number_of_threads = 100000
        LOGGER.info("Creating GThread Objects and Executing")
        start = perf_counter()
        LOGGER.info("StartTime is:%f", start)
        for i in range(number_of_threads):
            t_obj = GreenletThread(i, run=fun, x=1, y=2, z=3)
            t_obj.start()
            THREADS.append(t_obj)
        status, res = GreenletThread.terminate()
        LOGGER.info("All Threads successfully Completed:%s %s", status, res)
        self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        LOGGER.info("EndTime is:%f", end)
        LOGGER.info("Total Time Taken with running threads: %f", (end - start))
        LOGGER.info("-----------------------------------------------------------------------------")

    def test_separate_gthread(self):
        """
        Testing Greenlet Threading with passing function object or by overriding the _run
        if run=None.
        """
        LOGGER.info("Defining Number of Threads to be Started")
        LOGGER.info("Creating GThread Objects and Executing")
        start = perf_counter()
        LOGGER.info("StartTime is:%f", start)
        t1_obj = GreenletThread(0, run=fun, x=1, y=2, z=3)
        t2_obj = GreenletThread("Running fun1", run=fun1)
        t3_obj = GreenletThread("Running Default")
        t1_obj.start()
        t2_obj.start()
        t3_obj.start()
        THREADS.append(t1_obj)
        THREADS.append(t2_obj)
        THREADS.append(t3_obj)
        status, res = GreenletThread.terminate()
        LOGGER.info("All Threads successfully Completed:%s %s",status, res)
        self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        LOGGER.info("EndTime is:%f", end)
        LOGGER.info("Total Time Taken with running threads: %f", (end - start))
        LOGGER.info("----------------------------------------------------------------------------")

    def test_1000_gpool(self):
        """
        Testing Greenlet Threading with passing function object or by overriding the _run
        if run=None.
        """
        LOGGER.info("Defining Number of Threads to be Started")
        number_of_threads = 100000
        LOGGER.info("Creating GThread Objects and Executing")
        start = perf_counter()
        LOGGER.info("StartTime is:%f", start)
        gp_obj = GeventPool(number_of_threads)
        for i in range(number_of_threads):
            gp_obj.add_handler(fun1, i)
        gp_obj.join_group()
        gp_obj.shutdown()
        LOGGER.info("All Threads successfully Completed:")
        result = True
        self.assertTrue(result)
        end = perf_counter()
        LOGGER.info("EndTime is:%f", end)
        LOGGER.info("Total Time Taken with running threads: %f", (end - start))
        LOGGER.info("----------------------------------------------------------------------------")

    def test_gpool(self):
        """
        Testing Greenlet Threading with passing function object or by overriding the _run
        if run=None.
        """
        LOGGER.info("Defining Number of Threads to be Started")
        LOGGER.info("Creating GThread Objects and Executing")
        start = perf_counter()
        LOGGER.info("StartTime is:%f", start)
        gp_obj = GeventPool(3)
        gp_obj.add_handler(fun1, "First Method")
        gp_obj.add_handler(fun2, "Second Method")
        gp_obj.join_group()
        gp_obj.shutdown()
        LOGGER.info(gp_obj.result())
        LOGGER.info("All Threads successfully Completed:")
        result = True
        self.assertTrue(result)
        end = perf_counter()
        LOGGER.info("EndTime is:%f", end)
        LOGGER.info("Total Time Taken with running threads: %f", (end - start))
        LOGGER.info("---------------------------------------------------------------------------")


if __name__ == '__main__':
    unittest.main()
