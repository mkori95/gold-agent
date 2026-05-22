import boto3
import os
from boto3.dynamodb.conditions import Key
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)

_resource = None


def get_dynamo_resource():
    global _resource
    if _resource is None:
        _resource = boto3.resource(
            "dynamodb",
            region_name=os.environ.get("AWS_REGION_NAME", "ap-south-1"),
        )
    return _resource


def get_table(table_name: str):
    return get_dynamo_resource().Table(table_name)
