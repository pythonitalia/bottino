"""An AWS Python Pulumi program"""

from typing import cast
from pulumi.resource import ResourceOptions
from pulumi_aws import (
    lambda_,
    apigatewayv2,
    iam,
    ecr,
    get_caller_identity,
    route53,
    acm,
)
import pulumi
from pulumi_aws.lambda_._inputs import FunctionEnvironmentArgs

config = pulumi.Config()

domain_name = "bottino.pycon.it"

certificate = acm.Certificate(
    "certificate", domain_name=domain_name, validation_method="DNS"
)

pyconit_zone = route53.get_zone(name="pycon.it.", private_zone=False)

route_validation_1 = route53.Record(
    "cert-validation-1",
    allow_overwrite=True,
    name=certificate.domain_validation_options[0].resource_record_name,
    records=[certificate.domain_validation_options[0].resource_record_value],
    ttl=60,
    type=certificate.domain_validation_options[0].resource_record_type,
    zone_id=pyconit_zone.id,
)

certificate_validation = acm.CertificateValidation(
    "validation",
    certificate_arn=certificate.arn,
    validation_record_fqdns=[route_validation_1.fqdn],
)

api_domain = apigatewayv2.DomainName(
    "domain",
    domain_name="bottino.pycon.it",
    domain_name_configuration=apigatewayv2.DomainNameDomainNameConfigurationArgs(
        certificate_arn=certificate_validation.certificate_arn,
        endpoint_type="REGIONAL",
        security_policy="TLS_1_2",
    ),
)

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
    environment=FunctionEnvironmentArgs(
        variables={
            "SLACK_SIGNING_SECRET": config.get_secret("SLACK_SIGNING_SECRET"),
            "SLACK_BOT_TOKEN": config.get_secret("SLACK_BOT_TOKEN"),
            "IFFFT_WEBHOOK": config.get_secret("IFFFT_WEBHOOK"),
        }
    ),
)

gateway = apigatewayv2.Api(
    "bottino",
    protocol_type="HTTP",
    route_key="$default",
    target=bottino_fn.invoke_arn,
)

apigatewayv2.ApiMapping(
    "mapping",
    api_id=gateway.id,
    domain_name=api_domain.domain_name,
    stage="$default",
)

route53.Record(
    "domain",
    name=domain_name,
    type="A",
    zone_id=pyconit_zone.id,
    aliases=[
        route53.RecordAliasArgs(
            evaluate_target_health=False,
            name=api_domain.domain_name_configuration.target_domain_name,
            zone_id=api_domain.domain_name_configuration.hosted_zone_id,
        )
    ],
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
