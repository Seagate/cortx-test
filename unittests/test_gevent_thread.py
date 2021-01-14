import unittest
import logging
from time import perf_counter
from commons.gevent_thread import (GThread, threads)
logger = logging.getLogger(__package__)
logger.setLevel(logging.DEBUG)


def fun(*args, **kwargs):
    print("Executing with->:")
    print("Arguments:", args)
    print("and Keyword Arguments:", kwargs)
    return args


class MyTestCase(unittest.TestCase):

    def test_GThread(self, func=None):
        """Testing Greenlet Threading with passing function object or by overriding the _run if run=None
        """
        logger.info("Defining Number of Threads to be Started")
        number_of_threads = 4
        logger.info("Creating GThread Objects and Executing")
        start = perf_counter()
        logger.info("StartTime is:%f", start)
        for i in range(number_of_threads):
            t = GThread(i, run=fun, thread_id=i, x=1, y=2, z=3)
            t.start()
            threads.append(t)
        status, res = GThread.terminate()
        logger.info(f"All Threads successfully Completed:{status} {res}")
        self.assertTrue(status, f"All Threads successfully Completed: {res}")
        end = perf_counter()
        logger.info("EndTime is:%f", end)
        logger.info("Total Time Taken with running threads: %f", (end - start))


if __name__ == '__main__':
    unittest.main()
