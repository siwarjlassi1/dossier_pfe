# hp_chatbot_callbot/connect_stack.py

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_connect as connect,
    aws_iam as iam,
    aws_lambda as _lambda,
    Duration,
    CfnOutput,
)
from constructs import Construct


class ConnectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,
                 lex_bot_id: str,
                 lex_bot_alias_id: str,
                 orchestrator_arn: str,
                 **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── Instance Amazon Connect ──────────────────────────────────
        instance = connect.CfnInstance(
            self, "HpChatbotConnectInstance",
            attributes=connect.CfnInstance.AttributesProperty(
                inbound_calls=True,
                outbound_calls=False,
            ),
            identity_management_type="CONNECT_MANAGED",
            instance_alias="hp-chatbot-callbot",
        )

        # ── Permission : Connect peut invoquer Lex ───────────────────
        lex_role = iam.Role(
            self, "ConnectLexRole",
            assumed_by=iam.ServicePrincipal("connect.amazonaws.com"),
        )
        lex_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "lex:RecognizeText",
                    "lex:RecognizeUtterance",   # ← pour la voix
                    "lex:StartConversation",    # ← streaming vocal
                ],
                resources=["*"],
            )
        )

        # ── Intégration Lex dans Connect ─────────────────────────────
        # Association du bot Lex à l'instance Connect
        lex_bot = connect.CfnIntegrationAssociation(
            self, "ConnectLexIntegration",
            instance_id=instance.ref,
            integration_type="LEX_BOT",
            integration_arn=(
                f"arn:aws:lex:us-east-1:"
                f"{self.account}:bot-alias/"
                f"{lex_bot_id}/{lex_bot_alias_id}"
            ),
        )

        # ── Outputs ──────────────────────────────────────────────────
        self.instance_id  = instance.ref
        self.instance_arn = instance.attr_arn

        CfnOutput(self, "ConnectInstanceId",
                  value=instance.ref,
                  description="Amazon Connect Instance ID")

        CfnOutput(self, "ConnectInstanceArn",
                  value=instance.attr_arn,
                  description="Amazon Connect Instance ARN")

        CfnOutput(
            self, "ConnectConsoleUrl",
            value=(
                f"https://us-east-1.console.aws.amazon.com/"
                f"connect/v2/app/instances/{instance.ref}"
            ),
            description="URL Console Amazon Connect"
        )
