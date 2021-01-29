"""An AWS Python Pulumi program"""

from pulumi_aws import lambda_, apigatewayv2, iam, ecr, get_caller_identity
import pulumi


config = pulumi.Config()

iam_for_lambda = iam.Role(
    "bottino-lambda",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    }""",
)

iam.PolicyAttachment(
    "bottino-lambda-basic-execution-policy",
    roles=[iam_for_lambda],
    policy_arn=iam.ManagedPolicy.AWS_LAMBDA_BASIC_EXECUTION_ROLE,
)

docker_image = ecr.get_image(
    repository_name="bottino",
    image_tag="latest",
)

identify = get_caller_identity()
digest = docker_image.image_digest
image_uri = f"{identify.account_id}.dkr.ecr.eu-central-1.amazonaws.com/bottino@{digest}"

bottino_fn = lambda_.Function(
    "bottino",
    role=iam_for_lambda.arn,
    image_uri=image_uri,
    package_type="Image",
    environment={
        "variables": {
            "SLACK_SIGNING_SECRET": config.get_secret("SLACK_SIGNING_SECRET"),
            "SLACK_BOT_TOKEN": config.get_secret("SLACK_BOT_TOKEN"),
            "IFFFT_WEBHOOK": config.get_secret("IFFFT_WEBHOOK"),
        }
    },
)

gateway = apigatewayv2.Api(
    "bottino",
    protocol_type="HTTP",
    route_key="$default",
    target=bottino_fn.invoke_arn,
)


lambda_permission = lambda_.Permission(
    "bottino-apigateway-execution",
    action="lambda:InvokeFunction",
    function=bottino_fn.name,
    principal="apigateway.amazonaws.com",
    source_arn=gateway.execution_arn.apply(
        lambda execution_arn: f"{execution_arn}/*/*"
    ),
)
