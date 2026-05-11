import boto3

client = boto3.client('connect', region_name='us-east-1')

response = client.associate_lex_v2_bot(
    InstanceId='bc15b78b-02c3-4575-8686-e6c5b3767d7f',
    LexV2Bot={
        'AliasArn': 'arn:aws:lex:us-east-1:471112585335:bot-alias/OICNETXGXY/1RYBTPYOH6'
    }
)

print(response)
