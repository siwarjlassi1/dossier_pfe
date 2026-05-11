import aws_cdk as core
import aws_cdk.assertions as assertions

from hp_chatbot_callbot.hp_chatbot_callbot_stack import HpChatbotCallbotStack

# example tests. To run these tests, uncomment this file along with the example
# resource in hp_chatbot_callbot/hp_chatbot_callbot_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = HpChatbotCallbotStack(app, "hp-chatbot-callbot")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
