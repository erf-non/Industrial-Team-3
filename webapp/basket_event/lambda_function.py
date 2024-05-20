import sys

sys.path.append('./package')

import json
import boto3
import secrets
import time
import epcpy
import struct
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
                    ExpressionAttributeValues={":cid": {'SS': [conn_id]}},
                    ReturnValues="UPDATED_NEW"
                )


def send_response(body):
    response = mqtt.publish(
        topic='basket/event',
        qos=1,
        payload=json.dumps(body)
    )
    
def send_response2(body, client, topic):
    response = mqtt.publish(
        topic='basket/client/' + client  + '/' + topic,
        qos=0,
        payload=body
    )

def get_item_details(product_id):
    global db
    
    tin = product_id.split("#")[0] 
    return db.get_item(
        TableName='basket', 
        Key={"PK": {"S": "product_" + tin}, "SK": {"S": "ProductData"}}
    )
    
def put_session(client_id, sess_id):
    global db
    
    # map current session id to device id
    db.put_item(
        TableName='basket', 
        Item={"PK": {"S": "curr_sess_" + client_id},
            "SK": {"S": "SessionId"},
            "SessionId": {"S": sess_id}}
        )
    
    db.put_item(
        TableName='basket', Item={"PK": {"S": "session_" + sess_id}, 
        "SK": {"S": "SessionData"}, "TotalPrice": {"N": "0"}, 
        "TTL": {"N": str(round(time.time()) + 43200)}}) # hours 
        
def add_product_to_basket(session_id, product_id):
    global db
    
    item = get_item_details(product_id)
    
    if "Item" not in item:
        return None
    
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
        ws_notify(session_id, json.dumps({"event": "basket_update",
                                            "products": response["Attributes"].get("Products", {}).get("SS", []),
                                            "total": response["Attributes"]["TotalPrice"]["N"]}))
    
        return response["Attributes"]["TotalPrice"]["N"]
    except ClientError as e: 
        # This error is fine, means that the identical product (same uuid) already was in the basket 
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            print("product already is in baseket but it's okay: {}".format(e.response['Error']))
        else:
            print("database error: {}".format(e.response['Error']))
        return None
            

    
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
        ws_notify(session_id, json.dumps({"event": "basket_update",
                                            "products": response["Attributes"].get("Products", {}).get("SS", []),
                                            "total": response["Attributes"]["TotalPrice"]["N"]}))
        
        return response["Attributes"]["TotalPrice"]["N"]
    except ClientError as e: 
        # This error is fine, means that the identical product (same uuid) already was in the basket 
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            print("product isn't in the basket: {}".format(e.response['Error']))
        else:
            print("database error: {}".format(e.response['Error']))
        
        return None
    
def get_curr_session_by_device_id(device_id):
    global db
    
    result = db.get_item(
        TableName='basket', 
        Key={"PK": {"S": "curr_sess_" + device_id}, "SK": {"S": "SessionId"}}
    )
    
    return result.get("Item", {}).get("SessionId", {}).get("S", None)

def parse_epc_tag(epc):
    try:
        return epcpy.base64_to_tag_encodable(epc).epc_uri
    except:
        return None
    
def get_product_id(epc):
    epc_uri = parse_epc_tag(epc)
    if epc_uri:
        match epc_uri.split(":")[3]:
            case "giai":
                product_id = epc_uri.split(":")[4].replace(".", "#")
            case "sgtin":
                parts = epc_uri.split(":")[4].split(".")
                product_id = ".".join(parts[0:2]) + "#" + parts[2]
            case _:
                product_id = None
    else:
        product_id = None
        
    return product_id
            

def lambda_handler(event, context):
    global mqtt
    mqtt = boto3.client('iot-data', region_name='ap-northeast-2')
    global db
    db = boto3.client('dynamodb')
    
    send_response(json.dumps(event))
    
    match event["event"]:
        case "add_product":
            product_id = get_product_id(event["epc"])
            
            basket_price = add_product_to_basket(
                get_curr_session_by_device_id(event["client"]),
                product_id
            )
            
            send_response2("add prodoct: " + get_product_id(event["epc"]), event["client"], "debug")
            
            if basket_price:
                send_response2(struct.pack(">i", int(basket_price)), event["client"], "basket_total")
        case "remove_product":
            product_id = get_product_id(event["epc"])
            
            basket_price = remove_product_from_basket(
                get_curr_session_by_device_id(event["client"]),
                product_id
            )
            
            if basket_price:
                send_response2(struct.pack(">i", int(basket_price)), event["client"], "basket_total")
        case "start_session":
            session_id = secrets.token_urlsafe(6)
            put_session(event["client"], session_id)
            send_response2(session_id, event["client"], "session_id")

        case _:
            raise("Bad request")
    
    return {
        'statusCode': 200,
        'body': json.dumps("test")
    }
