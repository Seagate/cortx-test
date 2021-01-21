import unittest
import logging
from time import perf_counter
from commons.greenlet_worker import (GreenletThread, threads)
from commons.greenlet_worker import GeventPool

logger = logging.getLogger(__package__)
logger.setLevel(logging.DEBUG)


def fun(*args, **kwargs):
    print("Executing fun with->:")
    print("Arguments:{0} and Keyword Arguments {1} ", args, kwargs)
    return True


def fun1(x):
    print("Running fun1 Thread", x)
    return True


def fun2(y):
    print("Running fun2 Thread", y)
    return False


class MyTestCase(unittest.TestCase):

    def test_1000_GThread(self):
        """Testing Greenlet Threading with passing function object or by overriding the _run if run=None
        """
        logger.info("Defining Number of Threads to be Started")
        number_of_threads = 100000
        logger.info("Creating GThread Objects and Executing")
        start = perf_counter()
        logger.info("StartTime is:%f", start)
        for i in range(number_of_threads):
            t = GreenletThread(i, run=fun, x=1, y=2, z=3)
            t.start()
            threads.append(t)
        status, res = GreenletThread.terminate()
        logger.info(f"All Threads successfully Completed:{status} {res}")
        self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        logger.info("EndTime is:%f", end)
        logger.info("Total Time Taken with running threads: %f", (end - start))
        logger.info("-------------------------------------------------------------------------------------------------")

    def test_Separate_GThread(self):
        """Testing Greenlet Threading with passing function object or by overriding the _run if run=None
        """
        logger.info("Defining Number of Threads to be Started")
        logger.info("Creating GThread Objects and Executing")
        start = perf_counter()
        logger.info("StartTime is:%f", start)
        t1 = GreenletThread(0, run=fun, x=1, y=2, z=3)
        t2 = GreenletThread("Running fun1", run=fun1)
        t3 = GreenletThread("Running Default")
        t1.start()
        t2.start()
        t3.start()
        threads.append(t1)
        threads.append(t2)
        threads.append(t3)
        status, res = GreenletThread.terminate()
        logger.info(f"All Threads successfully Completed:{status} {res}")
        self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        logger.info("EndTime is:%f", end)
        logger.info("Total Time Taken with running threads: %f", (end - start))
        logger.info("-------------------------------------------------------------------------------------------------")

    def test_1000_GPool(self):
        """Testing Greenlet Threading with passing function object or by overriding the _run if run=None
        """
        logger.info("Defining Number of Threads to be Started")
        number_of_threads = 100000
        logger.info("Creating GThread Objects and Executing")
        start = perf_counter()
        logger.info("StartTime is:%f", start)
        gp = GeventPool(number_of_threads)
        for i in range(number_of_threads):
            gp.add_handler(fun1, i)
        gp.join_group()
        gp.shutdown()
        logger.info(f"All Threads successfully Completed:")
        # self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        logger.info("EndTime is:%f", end)
        logger.info("Total Time Taken with running threads: %f", (end - start))
        logger.info("-------------------------------------------------------------------------------------------------")

    def test_GPool(self):
        """Testing Greenlet Threading with passing function object or by overriding the _run if run=None
        """
        logger.info("Defining Number of Threads to be Started")
        logger.info("Creating GThread Objects and Executing")
        start = perf_counter()
        logger.info("StartTime is:%f", start)
        gp = GeventPool(3)
        gp.add_handler(fun1, "First Method")
        gp.add_handler(fun2, "Second Method")
        gp.join_group()
        gp.shutdown()
        logger.info(gp.result())
        logger.info(f"All Threads successfully Completed:")
        # self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        logger.info("EndTime is:%f", end)
        logger.info("Total Time Taken with running threads: %f", (end - start))
        logger.info("-------------------------------------------------------------------------------------------------")


if __name__ == '__main__':
    unittest.main()
