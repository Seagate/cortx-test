"""
Kafka consumer for distributed runner
"""
from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry.json_schema import JSONDeserializer
from confluent_kafka.serialization import StringDeserializer


def dict_to_kafka_msg(obj, ctx):
    """
    Converts object literal(dict) to a Kafka msg instance.
    Args:
        ctx (SerializationContext): Metadata pertaining to the serialization
            operation.
        obj (dict): Object literal(dict)
    """
    if obj is None:
        return None

    return KafkaMsg(te_id=obj['te_id'],
                    execution_type=obj['parallel'],
                    target_list=obj['target_list'],
                    test_list=obj['test_list'])


def get_consumer(args):
    """
      Form a consumer configuration
      Subscribe to a given topic
      :return consumer
    """
    json_deserializer = JSONDeserializer(SCHEMA_STR,
                                         from_dict=dict_to_kafka_msg)
    string_deserializer = StringDeserializer('utf_8')

    consumer_conf = {'bootstrap.servers' : args.bootstrap_servers,
                     'key.deserializer' : string_deserializer,
                     'value.deserializer' : json_deserializer,
                     'group.id' : args.group,
                     'auto.offset.reset' : "earliest"}

    consumer = DeserializingConsumer(consumer_conf)
    consumer.subscribe([args.topic])
    return consumer


class KafkaMsg:
    """
    Kafka msg format
    """

    def __init__(self, tag, parallel, test_set, te_tickets, targets, build):
        """
        Constructs the object from message on message bus.
        Args:
        tag (str): Most specific tag for test or test set.
        parallel (bool): Can be executed in parallel or not (True/False)
        test_set (set or string): tests to be executed.
        te_tickets (list): List of test execution tickets
        build (str): build number or string
        """
        self.tag = tag
        self.parallel = parallel
        self.te_tickets = te_tickets
        # test set should not be serialized, see convert_ticket_to_dict()
        self.test_list = list(test_set)
        self.target_list = targets
        self.build = build


SCHEMA_STR = """
            {
              "$schema": "http://json-schema.org/draft-07/schema#",
              "title": "Kakfa_msg",
              "description": "A Confluent Kafka Message Structure",
              "type": "object",
              "properties": {
               "tag": {
                  "description": "Tag",
                  "type": "string",
                },
                "build": {
                  "description": "build number",
                  "type": "string",
                },
                "te_tickets": {
                  "description": "List of test execution ids",
                  "type": "List"
                },
                "parallel": {
                  "description": "Execution type: parallel/non-parallel",
                  "type": "boolean",
                },
                "target_list": {
                  "description": "List of targets available for this execution",
                  "type": "List"
                },
                "test_list": {
                  "description": "List of tests to execute",
                  "type": "string"
                }

              },
              "required": [ "build", "parallel", "target_list", "test_list ]
            }
            """
