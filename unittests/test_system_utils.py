import pytest
import logging
from commons.utils import system_utils

def test_system_utils():
    system_utils.run_remote_cmd("pwd","10.237.65.202","root","seagate")