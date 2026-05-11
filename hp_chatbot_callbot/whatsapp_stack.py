import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    aws_iam as iam,
    Duration,
    CfnOutput,
)
from constructs import Construct
from hp_chatbot_callbot.dynamo_stack import DynamoStack

#Rôle : Expose un webhook pour recevoir les messages WhatsApp via Twilio



class WhatsappStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,
                 dynamo_stack: DynamoStack,
                 lex_bot_id: str,
                 lex_bot_alias_id: str,
                 **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── IAM Role pour Lambda WhatsApp ────────────────────────────
        whatsapp_role = iam.Role(
            self, "HpChatbotWhatsappRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Permission Secrets Manager
        whatsapp_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["*"],
            )
        )

        # Permission Lex
        whatsapp_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lex:RecognizeText"],
                resources=["*"],
            )
        )

        # ── Lambda WhatsApp ──────────────────────────────────────────
        whatsapp_fn = _lambda.Function(
            self, "WhatsappHandler",
            function_name="hp-chatbot-whatsapp",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/whatsapp"),
            role=whatsapp_role,
            timeout=Duration.seconds(30),
            environment={
                "LEX_BOT_ID": lex_bot_id,
                "LEX_BOT_ALIAS_ID": lex_bot_alias_id,
            },
        )

        # ── API Gateway ──────────────────────────────────────────────
        api = apigw.RestApi(
            self, "HpChatbotWhatsappApi",
            rest_api_name="hp-chatbot-whatsapp-api",
            description="API Gateway pour WhatsApp Twilio",
        )

        # /whatsapp → POST
        whatsapp_resource = api.root.add_resource("whatsapp")
        whatsapp_resource.add_method(
            "POST",
            apigw.LambdaIntegration(whatsapp_fn),
        )

        # ── Output ───────────────────────────────────────────────────
        CfnOutput(
            self, "WhatsappWebhookUrl",
            value=f"{api.url}whatsapp",
            description="URL à coller dans Twilio Webhook"
        )
