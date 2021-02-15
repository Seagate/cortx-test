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

    return Kafka_Msg(te_id=obj['te_id'],
                     execution_type=obj['execution_type'],
                     target_list=obj['target_list'],
                     test_list=obj['test_list'])


def get_consumer(args):
    json_deserializer = JSONDeserializer(schema_str,
                                         from_dict=dict_to_kafka_msg)
    string_deserializer = StringDeserializer('utf_8')

    consumer_conf = {'bootstrap.servers': args.bootstrap_servers,
                     'key.deserializer': string_deserializer,
                     'value.deserializer': json_deserializer,
                     'group.id': args.group,
                     'auto.offset.reset': "earliest"}

    consumer = DeserializingConsumer(consumer_conf)
    consumer.subscribe([args.topic])
    return consumer


class Kafka_Msg(object):
    """
    Kafka msg format
    Args:
        te_id (str): Test execution id
        execution_type (string): Execution type: parallel/sequential
        target_list (list): List of targets to be used for this execution
        test_list(list): List of tests to execute
    """

    def __init__(self, te_id=None, execution_type=None, target_list=None, test_list=None):
        self.te_id = te_id
        self.execution_type = execution_type
        self.target_list = target_list
        self.test_list = test_list


schema_str = """
            {
              "$schema": "http://json-schema.org/draft-07/schema#",
              "title": "Kakfa_msg",
              "description": "A Confluent Kafka Message Structure",
              "type": "object",
              "properties": {
                "te_id": {
                  "description": "Test execution id",
                  "type": "string"
                },
                "execution_type": {
                  "description": "Execution type: parallel/non-parallel",
                  "type": "string",
                },
                "target_list": {
                  "description": "List of targets available for this execution",
                  "type": "string"
                },
                "test_list": {
                  "description": "List of tests to execute",
                  "type": "string"
                }

              },
              "required": [ "te_id", "execution_type", "target_list", "test_list ]
            }
            """
