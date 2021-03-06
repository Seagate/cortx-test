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
from commons.params import BOOTSTRAP_SERVERS,TEST_EXEC_TOPIC


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
                    test_set=obj['test_list'],
                    te_tickets=obj['te_tickets'],
                    target_list=obj['target_list'],
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
                     'auto.offset.reset': "earliest"}

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
        self.te_tickets = kwargs.get('te_tickets')
        # test set should not be serialized, see convert_ticket_to_dict()
        self.test_list = list(kwargs.get('test_set'))
        self.target_list = kwargs.get('target_list')
        self.build = kwargs.get('build')
        self.build_type = kwargs.get('build_type')
        self.test_plan = kwargs.get('test_plan')

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
                "test_set": {
                  "description": "Set of tests to execute",
                  "type": "string"
                }
                 "build_type": {
                  "description": "type of build: release/stable",
                  "type": "string"
                }
                 "test_plan": {
                  "description": "test plan number",
                  "type": "string"
                }

              },
              "required": [ "build", "parallel", "target_list", "test_set", 
              "te_tickets", "build_type", "test_plan" ]
            }
            """
