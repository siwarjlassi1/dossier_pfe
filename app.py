import aws_cdk as cdk
from hp_chatbot_callbot.lex_stack import LexStack
from hp_chatbot_callbot.dynamo_stack import DynamoStack
from hp_chatbot_callbot.lambda_stack import LambdaStack
from hp_chatbot_callbot.api_stack import ApiStack
from hp_chatbot_callbot.whatsapp_stack import WhatsappStack
from hp_chatbot_callbot.agent_stack import AgentStack

app = cdk.App()

env = cdk.Environment(
    account="471112585335",
    region="us-east-1",
)

# 1. Dynamo
dynamo_stack = DynamoStack(app, "HpChatbotDynamoStack", env=env)

# 2. API Gateway + Microservices
api_stack = ApiStack(
    app,
    "HpChatbotApiStack",
    dynamo_stack=dynamo_stack,
    env=env,
)

# 3. Lambda Orchestrateur
lambda_stack = LambdaStack(
    app,
    "HpChatbotLambdaStack",
    dynamo_stack=dynamo_stack,
    api_url=api_stack.api_url,
    env=env,
)

# 4. Agent Bedrock (RAG + Raisonnement autonome)
agent_stack = AgentStack(
    app,
    "HpChatbotAgentStack",
    dynamo_stack=dynamo_stack,
    api_url=api_stack.api_url,
    knowledge_base_id="8DOMZOCGC2",
    env=env,
)

# 5. Lex
lex_stack = LexStack(
    app,
    "HpChatbotLexStack",
    orchestrator_arn=lambda_stack.orchestrator.function_arn,
    env=env
)

# 6. WhatsApp Stack
whatsapp_stack = WhatsappStack(
    app,
    "HpChatbotWhatsappStack",
    dynamo_stack=dynamo_stack,
    lex_bot_id=lex_stack.bot_id,
    lex_bot_alias_id=lex_stack.bot_alias_id,
    env=env,
)

# ── Dependencies ──────────────────────────────────────────────────
api_stack.add_dependency(dynamo_stack)
lambda_stack.add_dependency(api_stack)
agent_stack.add_dependency(dynamo_stack)   # ← Agent attend Dynamo
agent_stack.add_dependency(api_stack)      # ← Agent attend API
lex_stack.add_dependency(lambda_stack)
lex_stack.add_dependency(agent_stack)      # ← Lex attend l'Agent
whatsapp_stack.add_dependency(lex_stack)

app.synth()
