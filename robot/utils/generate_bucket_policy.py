"""Bucket Policy Utility"""
import json


def generate_json_policy(bucket_name):
    """
    Function to perform the various operations for json data
    :param bucket_name: create json policy as per bucket name
    :return: Json policy in string format
    """
    json_policy_data = {"Version": "2012-10-17",
                        "Statement": [{"Sid": "AddPerm",
                                       "Action": ["S3:GetObject"],
                                       "Effect": "Allow", "Resource": [],
                                       "Principal": "*"}]}
    json_policy_resource = json_policy_data["Statement"][0]["Resource"]
    json_policy_resource.append("arn:aws:s3:::" + bucket_name + "/*")
    return json.dumps(json_policy_data)


def match_json_policy(policy1, policy2):
    """
    Function to verify policies matches or not
    :param policy1:  json policy1
    :param policy2:  json policy2
    :return: Boolean value of match case
    """
    return json.loads(policy1) == json.loads(policy2)


def update_json_policy(policy):
    """
    Function to update json data to expected format for the policy.
    :param policy:  existing json policy
    :return: expected Json policy in string format
    """
    policy = json.loads(policy)
    policy["Statement"][0]["Action"].append("S3:PutObject")
    return json.dumps(policy)
