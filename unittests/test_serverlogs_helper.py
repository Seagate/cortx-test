import pytest
from commons.helpers import serverlogs_helper
from datetime import datetime

now = datetime.now()
current_time= now.strftime('%b  %#d %H:%M:%S')

def test_serverlogs_lib():
    #collect_logs_fromserver( st_time, file_type='all', node='all', end_time = current_time,test_id):

    start_time = "Dec 12 16:06:01"
    end_time = "Dec 12 16:12:07"

    serverlogs_helper.collect_logs_fromserver(st_time= start_time,
                                              end_time= end_time,
                                              file_type= "motr",
                                              node="node1",
                                              test_suffix= "077")