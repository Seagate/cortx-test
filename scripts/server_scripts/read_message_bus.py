#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
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
