import time
# from cortx.utils.message_bus import MessageConsumer
try:
    from cortx.utils.message_bus import MessageConsumer
except ImportError as import_error:
    print('Error: cortx-py-utils is not installed.',
          'Please install using yum install -y cortx-py-utils')

if __name__ == "__main__":
    consumer = MessageConsumer(consumer_id="sspl-test",
                               consumer_group="cortx_monitor",
                               message_types=["alerts"],
                               auto_ack=False, offset="latest")
    while True:
        try:
            message = consumer.receive(timeout=3)
            if message:
                consumer.ack()
                print(message)
            else:
                time.sleep(1)
        except Exception as e:
            print(e)
