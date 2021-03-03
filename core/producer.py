# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""SerializingProducer using JSON. A ticket is serialized using JSONSerializer"""
import argparse
import logging
import json
from typing import Any
from uuid import uuid4
from confluent_kafka import SerializingProducer
from confluent_kafka.serialization import StringSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONSerializer
from confluent_kafka.error import ValueSerializationError
from config.params import SCHEMA_REGISTRY, BOOTSTRAP_SERVERS

LOGGER = logging.getLogger(__name__)


class Ticket:
    """
    Ticket to be executed by test runner.
    """

    def __init__(self, tag, parallel, test_set, te_tickets, targets, build):
        """
        Constructs the object to be fed into Message bus.
        Args:
        tag (str): Most specific tag for test or test set.
        parallel (bool): Can be executed in parallel or not (True/False)
        test_set (set or string): tests to be executed.
        te_tickets (list): List of test execution tickets
        build (str): build number or string
        """
        self.tag = tag
        self.parallel = parallel
        # test set should not be serialized, see convert_ticket_to_dict()
        self.test_set = test_set
        self.te_tickets = te_tickets
        self.targets = targets
        self.build = build

    def __str__(self):
        print(' '.join([self.tag, str(self.parallel), str(self.targets), str(self.build),
                       str(self.te_tickets), str(self.test_set)]))


def convert_ticket_to_dict(ticket, ctx):
    """
    Returns a dict representation of a Ticket instance for serialization.
    Ticket's field which must not be serialized should be omitted from dict.
    Args:
        ticket (Ticket): Ticket instance.
        ctx (SerializationContext): Metadata pertaining to the serialization
            operation.
    Returns:
        dict: Dict populated with tickets attributes to be serialized.
    """
    return dict(tag=ticket.name,
                test_set=ticket.test_set,
                te_tickets=ticket.te_tickets,
                targets=ticket.targets,
                build=ticket.build,
                parallel=ticket.parallel)


def delivery_report(err, msg):
    """
    Reports the failure or success of a message delivery.
    Args:
        err (KafkaError): The error that occurred on None on success.
        msg (Message): The message that was produced or failed.
    Note:
        In the delivery report callback the Message.key() and Message.value()
        will be the binary format as encoded by any configured Serializers and
        not the same object that was passed to produce().
        If you wish to pass the original object(s) for key and value to delivery
        report callback we recommend a bound callback or lambda where you pass
        the objects along.
    """
    if err is not None:
        print("Delivery failed for User record {}: {}".format(msg.key(), err))
        return
    print('User record {} successfully produced to {} [{}] at offset {}'.format(
        msg.key(), msg.topic(), msg.partition(), msg.offset()))


def produce(producer, topic, uuid=None, value=None, on_delivery=delivery_report):
    """
    Produce the ticket message i.e. value to topic.
    :param producer:
    :param topic:
    :param uuid:
    :param value:
    :param on_delivery:
    """
    # Serve on_delivery callbacks from previous calls to produce()
    producer.poll(0.0)
    producer.produce(topic=topic, key=uuid, value=value,
                     on_delivery=on_delivery)
    print("\nFlushing records...")


def server(*args: Any) -> None:
    """
    Demon thread to read work queue items, process and call produce on them.
    :param args:
    :return:
    """
    topic, work_queue = args
    schema_str = {
      "title": "Ticket",
      "description": "A Test Set or single test to be executed by test runner",
      "type": "object",
      "properties": {
        "tag": {
          "description": "Test cases tag",
          "type": "string"
        },
        "test_set": {
          "description": "A set of test cases to be executed",
          "type": "list",
          "exclusiveMinimum": 0
        },
        "te_tickets": {
          "description": "Test execution tickets",
          "type": "string"
        },
        "targets": {
          "description": "Test execution tickets",
          "type": "string"
        },
        "build": {
          "description": "Build string or number",
          "type": "string"
        },
        "parallel": {
          "description": "Test execution can happen in parallel or not",
          "type": "bool"
        },

      },
      "required": [ "tag", "test_set", "te_tickets", "targets", "build", "parallel" ]
    }
    schema_str = json.dumps(schema_str)
    schema_registry_conf = {"url": SCHEMA_REGISTRY}
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    json_serializer = JSONSerializer(schema_str, schema_registry_client, convert_ticket_to_dict)

    producer_conf = {"bootstrap.servers": BOOTSTRAP_SERVERS,
                     "key.serializer": StringSerializer("utf_8"),
                     "value.serializer": json_serializer}

    producer = SerializingProducer(producer_conf)

    print("Producing user records to topic {}. ^C to exit.".format(topic))

    while True:
        try:
            work_item = work_queue.get()
            import pdb
            pdb.set_trace()
            if work_item is None:
                work_item.task_done()
                work_queue.task_done()
                break
            test_set = list(work_item.get())
            te_tickets = work_item.tickets
            ticket = Ticket(work_item.tag, work_item.parallel,
                            test_set, te_tickets, work_item.targets,
                            work_item.build)
            produce(producer, topic=topic, uuid=str(uuid4()), value=ticket,
                    on_delivery=delivery_report)
        except ValueError:
            print("Invalid input ticket, discarding record...")
            LOGGER.info("Invalid input ticket, skipping record %s", ticket)
            continue
        except ValueSerializationError as fault:
            print("Invalid input ticket, discarding record...")
            LOGGER.exception("Serialization error %s for ticket %s", fault, ticket)

    producer.flush()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SerializingProducer Example")
    parser.add_argument('-b', dest="bootstrap_servers", required=True,
                        help="Bootstrap broker(s) (host[:port])")
    parser.add_argument('-s', dest="schema_registry", required=True,
                        help="Schema Registry (http(s)://host[:port]")
    parser.add_argument('-t', dest="topic", default="test_execution_topic",
                        help="Topic name")
    opts = parser.parse_args()
    server()
