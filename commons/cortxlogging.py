"""
Extended log rotation class for cortx log files
"""
import os
import sys
import gzip
import shutil
import datetime
import logging
from logging import handlers

LOG_DIR = 'log'
LOG_FILE = 'cortx-test.log'


def init_loghandler(log) -> None:
    """Initialize logging with stream and file handlers."""
    log.setLevel(logging.DEBUG)
    make_log_dir(LOG_DIR)
    fh = logging.FileHandler(os.path.join(os.getcwd(), LOG_DIR, 'latest', LOG_FILE), mode='w')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    log.addHandler(fh)
    log.addHandler(ch)


def set_log_handlers(log, name, mode='w'):
    """Set stream and file handlers."""
    fh = logging.FileHandler(name, mode=mode)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    log.addHandler(fh)
    log.addHandler(ch)


def make_log_dir(dirpath) -> None:
    """Create dir if not exists.Don't throw error for existence."""
    if not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)


def get_frame():
    """Get current frame and name."""
    return sys._getframe().f_code.co_name


class CortxRotatingFileHandler(handlers.RotatingFileHandler):
    """
    Handler overriding the existing RotatingFileHandler for switching cortx-test log files
    when the current file reaches a certain size.
    """

    def __init__(self, filename="cortx-test.log", maxBytes=10485760, backupCount=5):
        """
        Initialization for cortx rotating file handler
        """
        self.baseFilename = filename
        super().__init__(filename=self.baseFilename, maxBytes=maxBytes, backupCount=backupCount)
        self.namer = self.log_namer
        self.rotator = self.log_rotator

    def log_namer(self, name):
        """
        Method to form log file name for rotation internally called by rotation_filename() method
        :param name: name of the base file
        :return: cortx rotated log file name e.g., cortx-test.log-YYYY-MM-DD-1.gz
        """
        return "{}-{}-{}.gz".format(self.baseFilename, str(datetime.date.today()), name.split('.')[-1])

    def log_rotator(self, source, dest):
        """
        Method to compress and rotate the current log when size limit is reached.
        :param source: current log file path
        :param dest: destination path for rotated file
        """
        with open(source, "rb") as sf:
            with gzip.open(dest, "wb", 9) as df:
                shutil.copyfileobj(sf, df)
        os.remove(source)
