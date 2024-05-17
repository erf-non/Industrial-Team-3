import json
import boto3
import secrets
import time
from botocore.exceptions import ClientError

def ws_notify(session_id, data):
    domain = '917jdxtwp1.execute-api.ap-northeast-2.amazonaws.com'
    stage = 'production'
    
    ws_client = boto3.client(
        "apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}"
    )
    
    print("ws notifications")
    global db
    session = db.get_item(TableName='basket', Key={
        "PK": {"S": "session_" + session_id}, 
        "SK": {"S": "SessionData"}}
    )
    
    print("sess", session)
    
    if "WSClients" in session["Item"]:
        for conn_id in session["Item"]["WSClients"]["SS"]:
            print("notifying {}".format(conn_id))
            try:
                r = ws_client.post_to_connection(Data=data, ConnectionId=conn_id)
            except ClientError:
                print("Couldn't post to connection {}.".format(conn_id))
            except ws_client.exceptions.GoneException:
                print("Connection {} is gone, removing.".format(conn_id))
                response = db.update_item(
                    TableName='basket',
                    Key={
                        'PK': {'S': 'session_' + session_id},
                        'SK': {'S': 'SessionData'}
                    },
                    UpdateExpression="DELETE WSClients :cid",
                    ExpressionAttributeValues={":cid": {'SS': [connection_id]}},
                    ReturnValues="UPDATED_NEW"
                )


def send_response(body):
    response = mqtt.publish(
        topic='basket/event',
        qos=1,
        payload=json.dumps(body)
    )

def get_item_details(id):
    global db
    return db.get_item(TableName='basket', Key={"PK": {"S": "product_" + id}, "SK": {"S": "ProductData"}})
    
def put_session(id):
    global db
    return db.put_item(TableName='basket', Item={"PK": {"S": "session_" + id}, 
        "SK": {"S": "SessionData"}, "TotalPrice": {"N": "0"}, 
        "TTL": {"N": str(round(time.time()) + 43200)}}) # hours 
        
def add_product_to_basket(session_id, product_id):
    global db
    
    item = get_item_details(product_id)
    ws_notify(session_id, json.dumps({"event": "add_product", "product_id": product_id}))
    
    try:
        response = db.update_item(
            TableName='basket',
            Key={
                'PK': {'S': 'session_' + session_id},
                'SK': {'S': 'SessionData'}
            },
            UpdateExpression="ADD TotalPrice :p, Products :idset",
            # Prevent updating the price when basket already contains an item with this uuid (duplicate messages on network layer, scanner errors etc.)
            ConditionExpression="NOT contains(Products, :id)",
            # API for UpdateExpression and ConditionExpression expect a different input type (once string, once set)
            ExpressionAttributeValues={":p": item["Item"]["Price"], ":idset": {'SS': [product_id]}, ":id": {'S': product_id}},
            ReturnValues="UPDATED_NEW"
        )
        print(response)
        #ws_notify(session_id, json.dumps({"event": "add_product", "product_id": product_id}))
    
    except ClientError as e: 
        # This error is fine, means that the identical product (same uuid) already was in the basket 
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            print("product already is in baseket but it's okay: {}".format(e.response['Error']))
        else:
            print("database error: {}".format(e.response['Error']))
            

    
def remove_product_from_basket(session_id, product_id):
    global db
    
    item = get_item_details(product_id)
    price = item["Item"]["Price"]["N"]
    price_neg = "-" + price
    
    try:
        response = db.update_item(
            TableName='basket',
            Key={
                'PK': {'S': 'session_' + session_id},
                'SK': {'S': 'SessionData'}
            },
            UpdateExpression="ADD TotalPrice :p DELETE Products :idset",
            # Prevent updating the price when basket doesn't contain an item with this uuid (duplicate messages on network layer, scanner errors etc.)
            ConditionExpression="contains(Products, :id)",
            # API for UpdateExpression and ConditionExpression expect a different input type (once string, once set)
            ExpressionAttributeValues={":p": {'N': price_neg}, ":idset": {'SS': [product_id]}, ":id": {'S': product_id}},
            ReturnValues="UPDATED_NEW"
        )
        print(response)
        ws_notify(session_id, product_id)
    
    except ClientError as e: 
        # This error is fine, means that the identical product (same uuid) already was in the basket 
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            print("product isn't in the basket: {}".format(e.response['Error']))
        else:
            print("database error: {}".format(e.response['Error']))
    

def lambda_handler(event, context):
    global mqtt
    mqtt = boto3.client('iot-data', region_name='ap-northeast-2')
    global db
    db = boto3.client('dynamodb')
    
    match event["event"]:
        case "add":
            item = get_item_details(event["product_id"])
            add_product_to_basket(event["session_id"], event["product_id"])
            send_response(item["Item"])
        case "remove":
            item = get_item_details(event["product_id"])
            remove_product_from_basket(event["session_id"], event["product_id"])
            send_response(item["Item"])
        case "start_session":
            session_id = secrets.token_hex(8)
            put_session(session_id)
            send_response({"session_id": session_id})
        case _:
            raise("Bad request")
    
    return {
        'statusCode': 200,
        'body': json.dumps("test")
    }




    