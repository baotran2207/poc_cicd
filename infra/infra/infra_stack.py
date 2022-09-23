from aws_cdk import Stack
from aws_cdk import aws_cloudformation as cl
from aws_cdk import (
    aws_s3 as s3,
)  # Duration,; aws_sqs as sqs,; aws_pipeline as pipeline_,
from constructs import Construct


class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
