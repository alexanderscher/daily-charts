import boto3
import json
from botocore.exceptions import ClientError
import os

lambda_client = boto3.client("lambda")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID_FREDDY")
USER_ID = os.getenv("SPOTIFY_USER_ID_FREDDY")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET_FREDDY")

CLIENT_ID_1 = os.getenv("SPOTIFY_CLIENT_ID_GOOGLE")
USER_ID_1 = os.getenv("SPOTIFY_USER_ID_GOOGLE")
CLIENT_SECRET_1 = os.getenv("SPOTIFY_CLIENT_SECRET_GOOGLE")


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
                "CLIENT_ID": CLIENT_ID,
                "USER_ID": USER_ID,
                "CLIENT_SECRET": CLIENT_SECRET,
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
                "CLIENT_ID": CLIENT_ID_1,
                "USER_ID": USER_ID_1,
                "CLIENT_SECRET": CLIENT_SECRET_1,
            },
        ]
    }

    for p in payload["charts"]:

        print(f"Invoking shazam-city-charts for {p}")
        response = invoke_lambda(p, "shazam-city-charts")
        print(response)
    return {"statusCode": 200, "body": "Lambdas invoked"}
