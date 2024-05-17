import boto3
import json
import logging
import secrets
import hmac
import decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            # wanted a simple yield str(o) in the next line,
            # but that would mean a yield on the line with super(...),
            # which wouldn't work (see my comment below), so...
            return (str(o) for o in [o])
        return super(DecimalEncoder, self).default(o)

def connect(session_id, connection_id):
    # todo error handling
    db = boto3.client('dynamodb')
    response = db.update_item(
        TableName='basket',
        Key={
            'PK': {'S': 'session_' + session_id},
            'SK': {'S': 'SessionData'}
        },
        UpdateExpression="ADD WSClients :cid",
        ExpressionAttributeValues={":cid": {'SS': [connection_id]}},
        ReturnValues="UPDATED_NEW"
    )

    return 200
    
def disconnect(session_id, connection_id):
    # todo error handling
    db = boto3.client('dynamodb')
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

    return 200
    
    
def product_search(table, term):
    return table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("SearchTerm").contains(term.lower())
    )

def lambda_handler(event, context):
    table = boto3.resource("dynamodb").Table("basket")
    ctx = event.get("requestContext", {})
    
    print(event.get("requestContext", {}))
    
    if 'http' in ctx:
        print("lambda invoked by http")
        if ctx['http']['path'] == '/search/products':
            search_term = event.get('queryStringParameters', {}).get('query')
            
            if search_term is None:
                return {"statusCode": 400}
            
            result = product_search(table, search_term)
            print(result)
            items = []
            
            if 'Items' in result:
                for item in result['Items']:
                    items.append({"name_en": item["ProductNameEN"], "product_id": item["PK"][len("product_"):]})
            else:
                return {"statusCode": 500}
                
            print(items)

            return {
              "statusCode": 200,
              "body": json.dumps({"products": items}),
              "headers": {
                "Content-Type": "application/json"
              }
            }
        elif ctx['http']['path'] == '/list/new':
            public_id  = secrets.token_hex(8)
            private_id = secrets.token_hex(16)
            
            table.put_item(Item={"PK": "list_" + public_id, 
                "SK": "ListMetadata", "PrivateID": private_id})
                
            return {
              "statusCode": 200,
              "body": json.dumps({"public_id": public_id, "private_id": private_id}),
              "headers": {
                "Content-Type": "application/json"
              } 
            }
            
            
    else:
        print("lambda invoked by ws")
        
        route_key = event.get("requestContext", {}).get("routeKey")
        connection_id = event.get("requestContext", {}).get("connectionId")
        if route_key is None or connection_id is None:
            return {"statusCode": 400}
        

        logger.info("Request: %s, use table %s.", route_key, table.name)
        
        
        response = {"statusCode": 200}
        if route_key == "$connect":
            session_id = event.get("queryStringParameters", {"sess": None}).get("sess")
            response["statusCode"] = connect(session_id, connection_id)
            print("connecting session_id {}".format(session_id))
        elif route_key == "$disconnect":
            pass
            #response["statusCode"] = disconnect(session_id, connection_id)
        elif route_key == "add_product":
            response["body"] = "hiiii {}".format(connection_id)
        elif route_key == "get_list":
            body = event.get("body")
            
            try:
                body = json.loads(body)["body"]
                public_id = body["public_id"]
            except:
                return {"statusCode": 400, "body": "Bad request"}
                
            try:
                data = table.get_item(Key={
                    "PK": "list_" + public_id, 
                    "SK": "ListData"
                })
                
                if 'Item' not in data:
                    raise "Invalid data"
            except:
                return {"statusCode": 404,  "body": "Not found"}
                
            print("xd", data)
            
            items = []
            
            try:
                for item in data['Item'].get('Items', []):  # Handle potential absence of 'Items' key
                    items.append({
                        "count": int(item["count"]),
                        "id": int(item["id"]),
                        "title": str(item["title"]),
                        "product_id": str(item["product_id"])
                    })
            except:
                return {"statusCode": 500,  "body": "Data invalid"}
            
            return {
              "statusCode": 200,
              "body": json.dumps({"event": "get_list", "items": items}, cls=DecimalEncoder),
              "headers": {
                "Content-Type": "application/json"
              } 
            }
        elif route_key == "update_list":
            body = event.get("body")
            
            try:
                body = json.loads(body)["body"]
                public_id = body["public_id"]
                private_id = body["private_id"]
                items = body["items"]
            except:
                return {"statusCode": 400}
                
            print(body)
            
            metadata = table.get_item(Key={
                "PK": "list_" + public_id, 
                "SK": "ListMetadata"
            })
            
            # time safe compr
            if hmac.compare_digest(metadata["Item"]["PrivateID"], private_id):
                print("xd", items)
                table.put_item(Item={
                    "PK": "list_" + public_id, 
                    "SK": "ListData",
                    "Items": items
                })
                
                return {
                  "statusCode": 200,
                  "body": json.dumps({"event": "update_list", "success": True}),
                  "headers": {
                    "Content-Type": "application/json"
                  }
                }
            
            else:
                return {
                  "statusCode": 403
                }
            
                
        elif route_key == "sendmessage":
            body = event.get("body")
            body = json.loads(body if body is not None else '{"msg": ""}')
            domain = event.get("requestContext", {}).get("domainName")
            stage = event.get("requestContext", {}).get("stage")
            if domain is None or stage is None:
                logger.warning(
                    "Couldn't send message. Bad endpoint in request: domain '%s', "
                    "stage '%s'",
                    domain,
                    stage,
                )
                response["statusCode"] = 400
            else:
                apig_management_client = boto3.client(
                    "apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}"
                )
                response["statusCode"] = handle_message(
                    table, connection_id, body, apig_management_client
                )
        else:
            response["statusCode"] = 404
        
        return response
        
        # todo: shopping list start, shopping list add, shopping list remove
        # todo: send basket on connectß