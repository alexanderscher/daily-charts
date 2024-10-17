import boto3
import json
from botocore.exceptions import ClientError

lambda_client = boto3.client("lambda")


def invoke_lambda(payload, function_name):
    print(f"Invoking {function_name} ")
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    return response


def lambda_handler(event, context):
    payload = {
        "charts": [
            {
                "links": [
                    (
                        "https://www.shazam.com/charts/top-50/united-states/los-angeles",
                        "US",
                    )
                ],
                "subject": "Shazam US Cities Report",
            },
            {
                "links": [
                    ("https://www.shazam.com/charts/top-50/canada/calgary", "CA"),
                    (
                        "https://www.shazam.com/charts/top-50/united-kingdom/belfast",
                        "UK",
                    ),
                    ("https://www.shazam.com/charts/top-50/australia/adelaide", "AU"),
                ],
                "subject": "Shazam Global Cities Report",
            },
        ]
    }

    for p in payload["charts"]:

        print(f"Invoking shazam-city-charts for {p}")
        response = invoke_lambda(p, "shazam-city-charts")
        print(response)
    return {"statusCode": 200, "body": "Lambdas invoked"}
