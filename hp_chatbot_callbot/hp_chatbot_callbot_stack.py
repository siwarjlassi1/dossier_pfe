# hp_chatbot_callbot/hp_chatbot_callbot_stack.py

import aws_cdk as cdk
from aws_cdk import Stack
from constructs import Construct

from hp_chatbot_callbot.dynamo_stack    import DynamoStack
from hp_chatbot_callbot.api_stack       import ApiStack
from hp_chatbot_callbot.lambda_stack    import LambdaStack
from hp_chatbot_callbot.lex_stack       import LexStack
from hp_chatbot_callbot.whatsapp_stack  import WhatsappStack
from hp_chatbot_callbot.connect_stack   import ConnectStack   # ← nouveau


class HpChatbotCallbotStack(Stack):

    def __init__(self, scope: Construct,
                 construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        env = {"account": "471112585335", "region": "us-east-1"}

        # ── 1. DynamoDB ───────────────────────────────────────────
        dynamo = DynamoStack(
            scope, "HpChatbotDynamoStack", env=env
        )

        # ── 2. API Gateway + Microservices ────────────────────────
        api = ApiStack(
            scope, "HpChatbotApiStack",
            dynamo_stack=dynamo, env=env
        )

        # ── 3. Lambda Orchestrateur ───────────────────────────────
        lmb = LambdaStack(
            scope, "HpChatbotLambdaStack",
            dynamo_stack=dynamo,
            api_url=api.api_url,
            env=env,
        )

        # ── 4. Lex Bot ────────────────────────────────────────────
        lex = LexStack(
            scope, "HpChatbotLexStack",
            orchestrator_arn=lmb.orchestrator.function_arn,
            env=env,
        )

        # ── 5. WhatsApp ───────────────────────────────────────────
        WhatsappStack(
            scope, "HpChatbotWhatsappStack",
            dynamo_stack=dynamo,
            lex_bot_id=lex.bot_id,
            lex_bot_alias_id=lex.bot_alias_id,
            env=env,
        )

        # ── 6. Amazon Connect (Callbot) ───────────────────────────
        ConnectStack(                                    # ← nouveau
            scope, "HpChatbotConnectStack",
            lex_bot_id=lex.bot_id,
            lex_bot_alias_id=lex.bot_alias_id,
            orchestrator_arn=lmb.orchestrator.function_arn,
            env=env,
        )
