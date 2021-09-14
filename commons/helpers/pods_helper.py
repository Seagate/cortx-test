#!/usr/bin/python
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

"""Module to maintain all common functions across component."""

import logging
import os
import posixpath
import re
import shutil
import stat
import time
import mdstat
from typing import Tuple
from typing import List
from typing import Union
from typing import Any
from commons import commands, const
from commons.helpers.host import Host

log = logging.getLogger(__name__)

namespace_map = {}


class LogicalNode(Host):
    """Class to maintain all common functions across component."""

    kube_commands = ('create', 'apply', 'config', 'get', 'explain',
                 'autoscale', 'patch', 'scale')

    def get_service_logs(self, svc_name: str, namespace: str, options: '') -> Tuple:
        """Get logs of a pod or service."""
        cmd = commands.FETCH_LOGS.format(svc_name, namespace, options)
        res = self.execute_cmd(cmd)
        return res

    def send_k8s_cmd(
            self,
            operation: str,
            pod: str,
            namespace: str,
            command_suffix: str,
            decode=False,
            **kwargs) -> list:
        """send/execute command on logical node/pods."""
        if operation not in LogicalNode.kube_commands:
            raise ValueError(
                "command parameter must be one of %r." % LogicalNode.kube_commands)
        out = []
        log.debug("Performing %s on service %s...", operation, pod, namespace)
        cmd = commands.KUBECTL_CMD.format(operation, pod, namespace, command_suffix)
        resp = self.execute_cmd(cmd, **kwargs)
        if decode:
            resp = resp.decode("utf8").strip()
        out.append(resp)
        return out

    def shutdown_node(self, options=None):
        """Function to shutdown any of the node."""
        try:
            cmd = "shutdown {}".format(options if options else "")
            log.debug(
                "Shutting down %s node using cmd: %s.",
                self.hostname,
                cmd)
            resp = self.execute_cmd(cmd, shell=False)
            log.debug(resp)
        except BaseException as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.shutdown_node.__name__, error)
            return False, error

        return True, "Node shutdown successfully"
