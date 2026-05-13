import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    Duration,
    CfnOutput,
)
from constructs import Construct
from hp_chatbot_callbot.dynamo_stack import DynamoStack


class LambdaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,
                 dynamo_stack: DynamoStack, api_url: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── IAM Role pour Lambda ─────────────────────────────────────
        lambda_role = iam.Role(
            self, "HpChatbotLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Permissions DynamoDB
        dynamo_stack.products_table.grant_read_data(lambda_role)
        dynamo_stack.orders_table.grant_read_write_data(lambda_role)
        dynamo_stack.complaints_table.grant_read_write_data(lambda_role)
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:Retrieve",
                    "bedrock:InvokeModel",
                ],
                resources=[
                    "arn:aws:bedrock:us-east-1:471112585335:knowledge-base/8DOMZOCGC2",
                    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
                    "*",
                ]
            )
        )

        # ── Lambda Orchestrateur ─────────────────────────────────────
        self.orchestrator = _lambda.Function(
            self, "HpChatbotOrchestrator",
            function_name="hp-chatbot-orchestrator",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/orchestrator"),
            role=lambda_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "BEDROCK_AGENT_ID":       "R604OPQQWY",
                "BEDROCK_AGENT_ALIAS_ID": "77RNRLMRAS",
                "API_GATEWAY_URL":        api_url,
                "KNOWLEDGE_BASE_ID":      "8DOMZOCGC2",
                "BEDROCK_MODEL_ARN":      "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
            },
        )

        # Permission : Lambda peut invoquer l'Agent Bedrock
        self.orchestrator.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeAgent"],
                resources=["*"]
            )
        )

        # ── Permission Comprehend ────────────────────────────────────
        self.orchestrator.add_to_role_policy(
            iam.PolicyStatement(
                actions=["comprehend:DetectSentiment"],
                resources=["*"]
            )
        )

        # ── Permission Lex → Lambda ──────────────────────────────────
        self.orchestrator.add_permission(
            "LexInvokePermission",
            principal=iam.ServicePrincipal("lexv2.amazonaws.com"),
            action="lambda:InvokeFunction",
        )

        # ── IAM Role pour les microservices ──────────────────────────
        microservice_role = iam.Role(
            self, "HpChatbotMicroserviceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # ── Lambda send-email ✅ SendGrid ────────────────────────────
        self.send_email = _lambda.Function(
            self, "SendEmailFunction",
            function_name="hp-send-email",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset(
                "lambda/microservices/send-email",
                ),
            role=microservice_role,
            timeout=Duration.seconds(15),
            memory_size=128,
            environment={
                "SENDER_EMAIL":      "jlassisywar776@gmail.com",
                "SENDGRID_API_KEY":  "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",  # ✅ Ta vraie clé SendGrid ici
                },
                )

           

        # ── Lambda track-claim ───────────────────────────────────────
        self.track_claim = _lambda.Function(
            self, "TrackClaimFunction",
            function_name="hp-track-claim",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/microservices/track-claim"),
            role=microservice_role,
            timeout=Duration.seconds(15),
            memory_size=128,
            environment={
                "COMPLAINTS_TABLE": dynamo_stack.complaints_table.table_name,
            },
        )

        # Permission DynamoDB pour track-claim
        dynamo_stack.complaints_table.grant_read_data(self.track_claim)

        # ── Outputs ──────────────────────────────────────────────────
        CfnOutput(
            self, "OrchestratorArn",
            value=self.orchestrator.function_arn
        )
        CfnOutput(
            self, "TrackClaimArn",
            value=self.track_claim.function_arn
        )
        CfnOutput(
            self, "SendEmailArn",
            value=self.send_email.function_arn
        )