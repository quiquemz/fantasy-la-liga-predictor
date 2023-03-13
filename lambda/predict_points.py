import os
import boto3
import json


ENDPOINT_NAME = 'la-liga-predict-score'
runtime = boto3.client('runtime.sagemaker')

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    
    data = json.loads(json.dumps(event))
    body = ','.join([str(x) for x in data.values()])
    
    response = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                       ContentType='text/csv',
                                       Body=body)
    
    try:
        return json.loads(response['Body'].read().decode())
    except:
        return 'Error: please make sure parameters are valid'