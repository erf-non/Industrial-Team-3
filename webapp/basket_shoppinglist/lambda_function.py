import boto3
import json
import logging
import secrets
import hmac
import decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

table = boto3.resource("dynamodb").Table("basket")

domain = '917jdxtwp1.execute-api.ap-northeast-2.amazonaws.com'
stage = 'production'
    
ws_client = boto3.client(
    "apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}"
)

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

def get_list_json(data):
    items = []
    
    try:
        for item in data:
            items.append({
                "count": int(item["count"]),
                "id": int(item["id"]),
                "title": str(item["title"]),
                "done": bool(item["done"]),
                "product_id": str(item["product_id"])
            })
    except:
       return None
    
    return json.dumps({"event": "get_list", "items": items}, cls=DecimalEncoder)
    
def search_handler(query):
    if query is None:
        return {"statusCode": 400}
            
    result = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("SearchTerm").contains(query.lower())
    )
    
    items = []
    
    if 'Items' in result:
        for item in result['Items']:
            items.append({"name_en": item["ProductNameEN"], "product_id": item["PK"][len("product_"):]})
    else:
        return {"statusCode": 500}

    return {
        "statusCode": 200,
        "body": json.dumps({"products": items}),
        "headers": {
        "Content-Type": "application/json"
        }
    }
    
def new_list_handler():
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

def get_list_handler(body, connection_id):
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
    except:
        return {"statusCode": 404,  "body": "Not found"}
        
    try:
        item = table.update_item(
            Key={
                "PK": "list_" + public_id, 
                "SK": "ListData"
            },
            UpdateExpression="ADD WSClients :connection_id",
            ExpressionAttributeValues={
                ':connection_id': set([connection_id])
            },
            ReturnValues="UPDATED_NEW"
        )
    except:
        return {"statusCode": 500, "body": "Failed to update WSClients"}
    

    try:
        body = get_list_json(data['Item'].get('ListItems', []))
    except:
        return {"statusCode": 500,  "body": "Failed to get list data"}

    if body == None:
        return {"statusCode": 500,  "body": "Data invalid"}
    
    return {
        "statusCode": 200,
        "body": body,
        "headers": {
        "Content-Type": "application/json"
        } 
    }
    
def update_list_handler(body, this_connection_id):
    try:
        body = json.loads(body)["body"]
        public_id = body["public_id"]
        private_id = body["private_id"]
        items = body["items"]
    except:
        return {"statusCode": 400}
    
    metadata = table.get_item(Key={
        "PK": "list_" + public_id, 
        "SK": "ListMetadata"
    })
    
    # time safe compr
    if hmac.compare_digest(metadata["Item"]["PrivateID"], private_id):
        table.update_item(
            Key={
                "PK": "list_" + public_id, 
                "SK": "ListData"
            },
            UpdateExpression="set ListItems = :i",
            ExpressionAttributeValues={
                ':i': items
            },
            ReturnValues="UPDATED_NEW"
        )
        
        #try:
        if True:
            data = table.get_item(Key={
              "PK": "list_" + public_id, 
              "SK": "ListData"
            })
            
            
            if "WSClients" in data["Item"]:
                for conn_id in data["Item"]["WSClients"]:
                    if conn_id != this_connection_id:
                        print("notifying {}".format(conn_id))
                        try:
                            r = ws_client.post_to_connection(Data=get_list_json(items), ConnectionId=conn_id)
                        except:
                            print("Couldn't post to connection {}.".format(conn_id))
                            table.update_item(
                                Key={
                                    "PK": "list_" + public_id, 
                                    "SK": "ListData"
                                },
                                UpdateExpression="DELETE WSClients :connection_id",
                                ExpressionAttributeValues={
                                    ':connection_id': set([conn_id])
                                },
                                ReturnValues="UPDATED_NEW"
                            )
        #except:
        #    print("Failed to notify clients!")
        
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
        
def get_item_details(product_id):
    tin = product_id.split("#")[0] 
    return table.get_item(
        Key={"PK": "product_" + tin, "SK": "ProductData"}
    ).get("Item", None)
        
def lambda_handler(event, context):
    ctx = event.get("requestContext", {}) 
    print(event.get("requestContext", {}))
    
    if 'http' in ctx:
        print("lambda invoked by http")
        if ctx['http']['path'] == '/search/products':
            search_term = event.get('queryStringParameters', {}).get('query')
            return search_handler(search_term)

        elif ctx['http']['path'] == '/list/new':
            return new_list_handler()
        
        elif ctx['http']['path'] == '/product/details':
            # validate that query string exists
            product_id = event.get('queryStringParameters', {}).get('product_id', None)
            if product_id is None:
                return {"statusCode": 400}
            
            return get_item_details(product_id)
    else:
        print("lambda invoked by ws")
        route_key = event.get("requestContext", {}).get("routeKey")
        connection_id = event.get("requestContext", {}).get("connectionId")
        if route_key is None or connection_id is None:
            return {"statusCode": 400}       

        response = {"statusCode": 200}
        
        if route_key == "$connect":
            session_id = event.get("queryStringParameters", {"sess": None}).get("sess")
            response["statusCode"] = connect(session_id, connection_id)
            print("connecting session_id {}".format(session_id))
        elif route_key == "$disconnect":
            pass
        elif route_key == "add_product":
            response["body"] = "hiiii {}".format(connection_id)
        elif route_key == "get_list":
            body = event.get("body")
            return get_list_handler(body, connection_id)
        elif route_key == "update_list":
            body = event.get("body")
            return update_list_handler(body, connection_id)
        else:
            response["statusCode"] = 404
        
        return response
        
        # todo: shopping list start, shopping list add, shopping list remove
        # todo: send basket on connectß