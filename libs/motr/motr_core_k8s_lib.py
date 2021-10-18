"""
Python library contains methods which provides the services endpoints.
"""

import json
import logging
from commons.helpers.pods_helper import LogicalNode
from config import CMN_CFG

log = logging.getLogger(__name__)

class MotrCoreK8s:
    
    def __init__(self):
        self.profile_fid = None
        self.cluster_info = None 
        self.node_obj = LogicalNode(hostname=CMN_CFG["nodes"][0]["hostname"],
                                username=CMN_CFG["nodes"][0]["username"],
                                password=CMN_CFG["nodes"][0]["password"])
        self.storage_nodes = self._get_storage_nodes_list
        self.node_dict = self._get_cluster_info
        self.num_nodes = len(self.storage_nodes)
    
    @property
    def _get_storage_nodes_list(self):
        """
        Returns all the storage node names
        """
        cmd = "kubectl get pods | awk '/storage-node/ {print $1}'"
        result = self.node_obj.execute_cmd(cmd=cmd, read_lines=True, exc=True)
        return [node.strip() for node in result]
         
    @property
    def _get_cluster_info(self):
        """
        Returns all the podNode's endpoints in a dict format
        """
        storage_node=self.storage_nodes[0]
        node_dict = {}
        cmd = "kubectl exec -it {} -c cortx-hax -- hctl status --json".format(storage_node)
        log.debug("Excuting commands inside hax container: {}".format(cmd))
        self.cluster_info = json.loads(self.node_obj.execute_cmd(cmd=cmd, exc=True))
        if self.cluster_info is not None:
            self.profile_fid = self.cluster_info["profiles"][0]["fid"]
            nodes_data = self.cluster_info["nodes"]
            for node in nodes_data:
                nodename = node["name"]
                node_dict[nodename] = {}
                node_dict[nodename]['m0client'] = []
                for svc in node["svcs"]:
                    if svc["name"] == "hax":
                        node_dict[nodename]['hax_fid'] = svc["fid"]
                        node_dict[nodename]['hax_ep'] = svc["ep"]
                    if svc["name"] == "m0_client":
                        node_dict[nodename]['m0client'].append({"ep":svc["ep"], "fid":svc["fid"]})
            return node_dict

    def get_primary_podNode(self):
        """ 
        To get the primary pod node name

        :returns: Primary(RC) node name in the cluster
        :rtype: str
        """
        storage_node=self.storage_nodes[0]
        cmd1 = "kubectl exec -it {} -c cortx-hax -- hctl status".format(storage_node)
        cmd2 = "awk -F ' '  '/(RC)/ { print $1 }'"
        cmd = cmd1 + " | " + cmd2
        log.debug("Excuting command inside hax container: {}".format(cmd))
        primary_node = self.node_obj.execute_cmd(cmd=cmd, read_lines=False, exc=True).strip().decode("utf-8") 
        return primary_node

    def get_podNode_endpoints(self, storage_node=None):
        """ 
        To get the endpoints details of the podNode/storage node
        
        :param storage_node: Name of the storage node
        :type: str
        :returns: Node dict of a storage node containing the endpoints details
        :rtype: dict
        """
        if not storage_node:
            storage_node = self.get_primary_podNode()
        for node in self.node_dict.keys():
            if node == storage_node:
                return self.node_dict[node]
