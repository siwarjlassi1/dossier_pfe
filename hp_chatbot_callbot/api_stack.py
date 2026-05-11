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


class ApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,
                 dynamo_stack: DynamoStack, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── IAM Role commun pour les microservices ───────────────────
        ms_role = iam.Role(
            self, "HpChatbotMicroserviceRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSESFullAccess"
                ),
            ],
        )
        dynamo_stack.products_table.grant_read_data(ms_role)
        dynamo_stack.orders_table.grant_read_write_data(ms_role)
        dynamo_stack.complaints_table.grant_read_write_data(ms_role)

        env_vars = {
            "PRODUCTS_TABLE":   dynamo_stack.products_table.table_name,
            "ORDERS_TABLE":     dynamo_stack.orders_table.table_name,
            "COMPLAINTS_TABLE": dynamo_stack.complaints_table.table_name,
        }

        # ── Lambda : Order ───────────────────────────────────────────
        order_fn = _lambda.Function(
            self, "OrderMicroservice",
            function_name="hp-chatbot-order",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/microservices/order"),
            role=ms_role,
            timeout=Duration.seconds(60),
            environment=env_vars,
        )

        # ── Lambda : Complaint ───────────────────────────────────────
        complaint_fn = _lambda.Function(
            self, "ComplaintMicroservice",
            function_name="hp-chatbot-complaint",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/microservices/complaint"),
            role=ms_role,
            timeout=Duration.seconds(30),
            environment=env_vars,
        )

        # ── Lambda : Verify Order ────────────────────────────────────
        verify_order_fn = _lambda.Function(
            self, "VerifyOrderMicroservice",
            function_name="hp-chatbot-verify-order",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/microservices/verify-order"),
            role=ms_role,
            timeout=Duration.seconds(30),
            environment=env_vars,
        )

        # ── Lambda : Track Claim ─────────────────────────────────────
        track_claim_fn = _lambda.Function(
            self, "TrackClaimMicroservice",
            function_name="hp-chatbot-track-claim",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/microservices/track-claim"),
            role=ms_role,
            timeout=Duration.seconds(30),
            environment=env_vars,
        )

        # ── Lambda : Send Email ──────────────────────────────────────
        send_email_fn = _lambda.Function(
            self, "SendEmailMicroservice",
            function_name="hp-chatbot-send-email",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/microservices/send-email"),
            role=ms_role,
            timeout=Duration.seconds(30),
            environment={
                **env_vars,
                "SENDER_EMAIL": "jlassisywar776@gmail.com",
            },
        )

        # ── Lambda : Chat (pont React → Lex) ─────────────────────────
        chat_fn = _lambda.Function(
            self, "ChatMicroservice",
            function_name="hp-chatbot-chat",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambda/microservices/chat"),
            role=ms_role,
            timeout=Duration.seconds(30),
            environment={
                "LEX_BOT_ID":       "OICNETXGXY",
                "LEX_BOT_ALIAS_ID": "1RYBTPYOH6",
                "LEX_LOCALE_ID":    "fr_FR",
            },
        )

        # Permission Lex pour la Lambda Chat
        chat_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["lex:RecognizeText"],
                resources=["*"]
            )
        )

        # ── API Gateway ──────────────────────────────────────────────
        api = apigw.RestApi(
            self, "HpChatbotApi",
            rest_api_name="hp-chatbot-api",
            description="API Gateway pour les microservices HP Chatbot",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type"],
            ),
        )

        # /order → POST
        order_resource = api.root.add_resource("order")
        order_resource.add_method(
            "POST",
            apigw.LambdaIntegration(order_fn),
        )

        # /complaint → POST
        complaint_resource = api.root.add_resource("complaint")
        complaint_resource.add_method(
            "POST",
            apigw.LambdaIntegration(complaint_fn),
        )

        # /verify-order → POST
        verify_order_resource = api.root.add_resource("verify-order")
        verify_order_resource.add_method(
            "POST",
            apigw.LambdaIntegration(verify_order_fn),
        )

        # /track-claim → POST
        track_claim_resource = api.root.add_resource("track-claim")
        track_claim_resource.add_method(
            "POST",
            apigw.LambdaIntegration(track_claim_fn),
        )

        # /send-email → POST
        send_email_resource = api.root.add_resource("send-email")
        send_email_resource.add_method(
            "POST",
            apigw.LambdaIntegration(send_email_fn),
        )

        # /chat → POST (pour le frontend React)
        chat_resource = api.root.add_resource("chat")
        chat_resource.add_method(
            "POST",
            apigw.LambdaIntegration(chat_fn),
        )

        # ── Outputs ──────────────────────────────────────────────────
        self.api_url = api.url

        CfnOutput(self, "ApiUrl",         value=api.url)
        CfnOutput(self, "OrderUrl",       value=f"{api.url}order")
        CfnOutput(self, "ComplaintUrl",   value=f"{api.url}complaint")
        CfnOutput(self, "VerifyOrderUrl", value=f"{api.url}verify-order")
        CfnOutput(self, "TrackClaimUrl",  value=f"{api.url}track-claim")
        CfnOutput(self, "SendEmailUrl",   value=f"{api.url}send-email")
        CfnOutput(self, "ChatUrl",        value=f"{api.url}chat")
