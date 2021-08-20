# Seagate license
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
""" Kafka consumer for distributed runner
"""
from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry.json_schema import JSONDeserializer
from confluent_kafka.serialization import StringDeserializer
from commons.params import BOOTSTRAP_SERVERS,TEST_EXEC_TOPIC,MAX_POLL_INTERVAL_MS,FETCH_MAX_WAIT_MS


def dict_to_kafka_msg(obj, ctx):
    """
    Converts object literal(dict) to a Kafka msg instance.
    Args:
        ctx (SerializationContext): Metadata pertaining to the serialization
            operation.
        obj (dict): Object literal(dict)
    """
    if obj is None or ctx is None:
        return None

    return KafkaMsg(tag=obj['tag'],
                    parallel=obj['parallel'],
                    test_set=obj['test_set'],
                    te_ticket=obj['te_ticket'],
                    targets=obj['targets'],
                    build=obj['build'],
                    build_type=obj['build_type'],
                    test_plan=obj['test_plan'])


def get_consumer():
    """
      Form a consumer configuration
      Subscribe to a given topic
      :return consumer
    """
    json_deserializer = JSONDeserializer(SCHEMA_STR,
                                         from_dict=dict_to_kafka_msg)
    string_deserializer = StringDeserializer('utf_8')

    consumer_conf = {'bootstrap.servers': BOOTSTRAP_SERVERS,
                     'key.deserializer': string_deserializer,
                     'value.deserializer': json_deserializer,
                     'group.id': TEST_EXEC_TOPIC,
                     'auto.offset.reset': "earliest",
                     'max.poll.interval.ms': MAX_POLL_INTERVAL_MS,
                     'fetch.max.wait.ms': FETCH_MAX_WAIT_MS
                     }

    consumer = DeserializingConsumer(consumer_conf)
    consumer.subscribe([TEST_EXEC_TOPIC])
    return consumer


class KafkaMsg:
    """
    Kafka msg format
    """

    def __init__(self, **kwargs):
        """
        Constructs the object from message on message bus.
        Args:
        tag (str): Most specific tag for test or test set.
        parallel (bool): Can be executed in parallel or not (True/False)
        test_set (set or string): tests to be executed.
        te_tickets (list): List of test execution tickets
        build (str): build number or string
        """
        self.tag = kwargs.get('tag')
        self.parallel = kwargs.get('parallel')
        self.te_ticket = kwargs.get('te_ticket')
        # test set should not be serialized, see convert_ticket_to_dict()
        self.test_list = list(kwargs.get('test_set'))
        self.target_list = list(kwargs.get('targets'))
        self.build = kwargs.get('build')
        self.test_plan = kwargs.get('test_plan')
        self.build_type = kwargs.get('build_type')

    def get_build_number(self):
        """
        Get build number
        """
        return self.build

    def get_target_list(self):
        """
        Get target list from kafka msg
        """
        return self.target_list


SCHEMA_STR = """
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "title": "Ticket",
      "description": "A Test Set or single test TBE by test runner",
      "type": "object",
      "properties": {
            "tag": {
                "description": "Test cases tag",
                "type": "string"
            },
            "test_set": {
                "description": "A set of test cases to be executed",
                "type": "array",
                "items": { "type": "string" }
            },
            "te_ticket": {
                "description": "Test execution tickets",
                "type": "string"
            },
            "targets": {
                "description": "Test execution targets",
                "type": "array",
                "items": { "type": "string" }
            },
            "build": {
                "description": "Build string or number",
                "type": "string",
                "default": "000"
            },
            "build_type": {
                "description": "Build type string",
                "type": "string"
            },
            "test_plan": {
                "description": "Test plan ticket",
                "type": "string"
            },
            "parallel": {
                "description": "Test execution can happen in parallel or not",
                "type": "boolean"
            }

        },
        "required": ["tag", "test_set", "te_ticket", "targets", "build", 
        "build_type", "test_plan", "parallel"]
    }
    """
