"""
Extended log rotation class for cortx log files
"""
import os
import gzip
import shutil
import datetime
from logging import handlers


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
