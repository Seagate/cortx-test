#!/usr/bin/env python3

import sys
import json
import traceback
import os
from cortx.utils.message_bus import MessageConsumer


if __name__ == '__main__':
    pid = os.fork()
    if pid == 0:
        consumer = MessageConsumer(consumer_id="1",
                                    consumer_group='event_mgr_test',
                                    message_types=["ha_event_hare"],
                                    auto_ack=False, offset='earliest')

        while True:
            try:
                print("In receiver")
                message = consumer.receive(timeout=0)

                msg = json.loads(message.decode('utf-8'))
                print(msg)
                consumer.ack()
                with open('/root/file.txt', 'w') as f:
                    print(msg, file=f)
            except Exception as exc:
                print(exc)
                print(traceback.format_exc())
                sys.exit(0)
    sys.exit(0)