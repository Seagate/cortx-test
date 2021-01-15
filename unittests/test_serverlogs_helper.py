import pytest
from commons.helpers import serverlogs_helper
from datetime import datetime

now = datetime.now()
current_time = now.strftime('%b  %#d %H:%M:%S')


def test_serverlogs_lib():
    # Before running following unit test, make sure the corrsponding file is placed
    # on the nodes/server
    start_time = "Dec 12 16:06:01"
    end_time = "Dec 12 16:12:07"
    serverlogs_helper.collect_logs_fromserver(st_time=start_time,
                                              end_time=end_time,
                                              file_type="motr",
                                              node="node1",
                                              test_suffix="0707")
    
