import json
import boto3
import os

lambda_client = boto3.client('lambda')

def handle(intent_request):
    """
    Gère l'intent de résumé de réclamation
    """
    
    session_attributes = intent_request.get('sessionAttributes', {})
    conversation_id = session_attributes.get('conversation_id', 'unknown')
    
    # Récupérer l'historique de conversation depuis DynamoDB
    dialogue = get_conversation_history(conversation_id)
    
    if not dialogue:
        return {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Failed',
                'message': {
                    'contentType': 'PlainText',
                    'content': 'Aucune conversation à résumer.'
                }
            }
        }
    
    # Appeler la Lambda de résumé
    try:
        response = lambda_client.invoke(
            FunctionName=os.environ['SUMMARIZE_LAMBDA_ARN'],
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'dialogue': dialogue,
                'conversation_id': conversation_id
            })
        )
        
        result = json.loads(response['Payload'].read())
        body = json.loads(result['body'])
        
        if body['success']:
            summary = body['summary']
            
            # Sauvegarder le résumé dans DynamoDB
            save_summary(conversation_id, summary, body['details'])
            
            return {
                'sessionAttributes': session_attributes,
                'dialogAction': {
                    'type': 'Close',
                    'fulfillmentState': 'Fulfilled',
                    'message': {
                        'contentType': 'PlainText',
                        'content': f"Voici le résumé de votre conversation :\n\n{summary}"
                    }
                }
            }
        else:
            raise Exception(body.get('error', 'Unknown error'))
    
    except Exception as e:
        print(f"❌ Erreur lors du résumé: {str(e)}")
        return {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close',
                'fulfillmentState': 'Failed',
                'message': {
                    'contentType': 'PlainText',
                    'content': 'Désolé, je n\'ai pas pu générer le résumé.'
                }
            }
        }

def get_conversation_history(conversation_id):
    """Récupère l'historique de conversation depuis DynamoDB"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['CONVERSATIONS_TABLE'])
    
    try:
        response = table.get_item(Key={'conversation_id': conversation_id})
        if 'Item' in response:
            messages = response['Item'].get('messages', [])
            # Formater en dialogue
            dialogue = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in messages
            ])
            return dialogue
    except Exception as e:
        print(f"❌ Erreur DynamoDB: {str(e)}")
    
    return ""

def save_summary(conversation_id, summary, details):
    """Sauvegarde le résumé dans DynamoDB"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['CONVERSATIONS_TABLE'])
    
    try:
        table.update_item(
            Key={'conversation_id': conversation_id},
            UpdateExpression='SET summary = :summary, summary_details = :details',
            ExpressionAttributeValues={
                ':summary': summary,
                ':details': details
            }
        )
        print(f"✅ Résumé sauvegardé pour {conversation_id}")
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {str(e)}")
