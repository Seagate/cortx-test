import pytest
import logging
from commons.utils import system_utils

def test_system_utils():
    system_utils.run_remote_cmd("pwd","10.237.65.202","root","seagate")
    system_utils.run_local_cmd('dir') 
    system_utils.is_path_exists('/home')
    system_utils.is_path_exists("C:\\Users\\532698\\Documents\\EOS\\workspace\\eos-test\\eos_test\\utility")
    system_utils.open_empty_file("C:\\Users\\532698\\Documents\\a.txt")
    system_utils.listdir("C:\\Users\\532698\\Documents\\EOS\\workspace\\eos-test\\eos_test\\utility")
    system_utils.makedir()

