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

##########################################################################
# Standard libraries
##########################################################################
import logging

##########################################################################
# Local libraries
##########################################################################
from commons.helpers.host import Host
##########################################################################
# Constants
##########################################################################
log = logging.getLogger(__name__)
##########################################################################
# salt functions
##########################################################################


class SaltHelper(Host):

    def get_pillar_values(
            self,
            component,
            keys,
            decrypt=False):
        """
        Fetch pillar values for given keys from given component
        :param str component: name of pillar component to fetch value from
        :param list keys: list of level wise nested keys e.g., [0th level, 1st level,..]
        :param bool decrypt: True for decrypted output
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: True/False and pillar output value
        :rtype: bool, str
        """
        pillar_key = ":".join([component, *keys])
        get_pillar_cmd = "salt-call pillar.get {} --output=newline_values_only".format(
            pillar_key)
        log.info(
            "Fetching pillar value with cmd: {}".format(get_pillar_cmd))
        output = self.execute_cmd(cmd=get_pillar_cmd, shell=False)
        output = output.decode() if isinstance(output, bytes) else output
        if not output:
            err_msg = "Pillar value not found for {}".format(pillar_key)
            return False, err_msg

        pillar_value = output.strip("\n")
        log.info(
            "Pillar value for {} is {}".format(
                pillar_key, pillar_value))
        if decrypt:
            if len(pillar_value) != 100:
                err_msg = "Invalid Token passed for decryption: {}".format(
                    pillar_value)
                return False, err_msg
            decrypt_cmd = "salt-call lyveutil.decrypt {} {} --output=newline_values_only".format(
                component, pillar_value)
            output = self.execute_cmd(decrypt_cmd, shell=False)
            output = output.decode() if isinstance(output, bytes) else output
            pillar_value = output.strip("\n")
            log.info(
                "Decrypted Pillar value for {} is {}".format(
                    pillar_key, pillar_value))

        return True, pillar_value
