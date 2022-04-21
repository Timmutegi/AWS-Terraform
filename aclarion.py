import boto3
import logging
import json
from botocore.exceptions import ClientError
import uuid
import argparse

# %22https://www.facebook.com/favicon.ico%22
# https://hands-on.cloud/working-with-aws-lambda-in-python-using-boto3/#How-to-create-Lamda-function-using-Boto3
# https://hands-on.cloud/working-with-sqs-in-python-using-boto3/
# https://hands-on.cloud/introduction-to-boto3-library/
# https://www.learnaws.org/2020/12/17/aws-sqs-boto3-guide/
# https://lifesaver.codes/answer/how-to-add-an-api-endpoint-for-a-lambda-function-572

AWS_REGION = "us-east-1"

# logger config
logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


def get_account_id():
    """
    Get the ID of the AWS account being used

    :return: ID of the account
    """
    sts = boto3.client("sts")
    try:
        response = sts.get_caller_identity()
    except ClientError as e:
        logging.error(e)

    else:
        logger.info("Account ID returned successfully.")
        return response["Account"]


def add_lambda_permission(data):
    """
    Add permission for the lambda function to be invoked

    :param data: Dictionary containing the AWS region, AWS account ID, REST API ID and lambda function name
    """
    source_arn = "arn:aws:execute-api:{aws-region}:{aws-acct-id}:{aws-api-id}/*/POST/{lambda-function-name}".format(
        **data
    )

    aws_lambda = boto3.client("lambda", region_name=AWS_REGION)

    try:
        aws_lambda.add_permission(
            FunctionName=data["lambda-function-name"],
            StatementId=uuid.uuid4().hex,
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=source_arn,
        )

    except ClientError as e:
        logging.error(e)

    else:
        logger.info("Lambda permission added successfully.")


def create_lambda_execution_role():
    """
    Create a lambda execution role
    """
    iam = boto3.client("iam")

    role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        response = iam.create_role(
            RoleName="LambdaBasicExecution",
            AssumeRolePolicyDocument=json.dumps(role_policy),
        )
    except ClientError as e:
        logging.error(e)

    else:
        logger.info("Lambda execution role created successfully.")


def create_api_execution_role():
    """
    Create an API Gateway execution role
    """
    iam = boto3.client("iam")

    role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {
                    "Service": ["apigateway.amazonaws.com", "lambda.amazonaws.com"]
                },
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        response = iam.create_role(
            RoleName="aclarionRole",
            AssumeRolePolicyDocument=json.dumps(role_policy),
        )

    except ClientError as e:
        logging.error(e)

    else:
        logger.info("API execution role created successfully.")


def get_lambda_execution_role():
    """
    Get the lambda execution IAM role

    :return: Role
    """
    # Create IAM client
    iam_client = boto3.client("iam")

    try:
        role = iam_client.get_role(RoleName="LambdaBasicExecution")

    except ClientError as e:
        logging.error(e)

    else:
        logger.info("Lambda execution role retured successfully.")

        return role


def create_bucket(bucket_name, region=None):
    """
    Create an S3 bucket in a specified region

    If a region is not specified, the bucket is created in the S3 default
    region (us-east-1).

    :param bucket_name: Bucket to create
    :param region: String region to create bucket in, e.g., 'us-west-2'

    """

    # Create bucket
    try:
        if region is None:
            s3_client = boto3.client("s3")
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client = boto3.client("s3", region_name=region)
            location = {"LocationConstraint": region}
            s3_client.create_bucket(
                Bucket=bucket_name, CreateBucketConfiguration=location
            )
    except ClientError as e:
        logging.error(e)

    else:
        logger.info(f"{bucket_name} created successfully.")


def fetch_buckets():
    """
    Fetch existing S3 buckets
    """
    try:
        s3 = boto3.client("s3")
        response = s3.list_buckets()

        # Output the bucket names
        print("Existing buckets:")
        for bucket in response["Buckets"]:
            print(f'  {bucket["Name"]}')

    except ClientError as e:
        logging.error(e)


def create_lambda_function(lambda_function_name, role):
    """
    Create a lambda function

    :param lambda_function_name: Name of the lambda function to be created
    :param role: IAM policy

    """
    try:
        with open("./lambda/lambda.zip", "rb") as f:
            zipped_code = f.read()

        lambda_client = boto3.client("lambda")

        response = lambda_client.create_function(
            FunctionName=lambda_function_name,
            Runtime="python3.9",
            Role=role["Role"]["Arn"],
            Handler="handler.lambda_handler",
            Code=dict(ZipFile=zipped_code),
            Timeout=300,
        )

    except ClientError as e:
        logging.error(e)

    else:
        logger.info("Lambda function created successfully.")
        return response["FunctionArn"]


def create_rest_api(api_name):
    """
    Creates a REST API on API Gateway. The default API has only a root resource
    and no HTTP methods.

    :param api_name: The name of the API. This descriptive name is not used in
                        the API path.
    :return: The ID of the newly created API.
    """
    try:
        api_client = boto3.client("apigateway")
        rest_api = api_client.create_rest_api(name=api_name)

    except ClientError as e:
        logging.error(e)
    else:
        logger.info("REST API created successfully.")
        return rest_api["id"]


def get_api_root_id(rest_api_id):
    """
    Get the API root ID

    :param rest_api_id: The ID of the API
    :return: The ID of the root resource
    """
    api_client = boto3.client("apigateway")
    # Get the rest api's root id
    try:
        root_resource_id = api_client.get_resources(restApiId=rest_api_id)["items"][0][
            "id"
        ]

    except ClientError as e:
        logging.error(e)
    else:
        return root_resource_id


def create_api_resource(rest_api_id, root_resource_id, lambda_function_name):
    """
    Create a resource for the API

    :param rest_api_id: The ID of the API
    :return: The ID of the root resource
    """
    api_client = boto3.client("apigateway")

    try:
        # Create an api resource
        api_resource = api_client.create_resource(
            restApiId=rest_api_id,
            parentId=root_resource_id,
            pathPart=lambda_function_name,
        )

    except ClientError as e:
        logging.error(e)
    else:
        logger.info("API resource created successfully.")

        return api_resource["id"]


def create_post_method(rest_api_id, API_RESOURCE_ID):
    """
    Create a POST method for the API

    :param rest_api_id: The ID of the API
    :param API_RESOURCE_ID: The ID of the root resource of the API
    """
    # Add a post method to the rest api resource
    api_client = boto3.client("apigateway")
    try:
        api_method = api_client.put_method(
            restApiId=rest_api_id,
            resourceId=API_RESOURCE_ID,
            httpMethod="POST",
            authorizationType="NONE",
            apiKeyRequired=True,
        )

        put_method_res = api_client.put_method_response(
            restApiId=rest_api_id,
            resourceId=API_RESOURCE_ID,
            httpMethod="POST",
            statusCode="200",
        )

    except ClientError as e:
        logging.error(e)
    else:
        logger.info("API POST method created successfully.")


def deploy(rest_api_id, API_RESOURCE_ID, arn_uri):
    """
    Deploy the API

    :param rest_api_id: The ID of the API
    :param API_RESOURCE_ID: The ID of the root resource of the API
    :arn_uri: The uri of the REST API
    """
    arn_uri = (
        "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/"
        + arn_uri
        + "/invocations"
    )

    api_client = boto3.client("apigateway")

    try:
        put_integration = api_client.put_integration(
            restApiId=rest_api_id,
            resourceId=API_RESOURCE_ID,
            httpMethod="POST",
            type="AWS",
            integrationHttpMethod="POST",
            uri=arn_uri,
        )

        put_integration_response = api_client.put_integration_response(
            restApiId=rest_api_id,
            resourceId=API_RESOURCE_ID,
            httpMethod="POST",
            statusCode="200",
            selectionPattern=".*",
        )

        deployment = api_client.create_deployment(
            restApiId=rest_api_id,
            stageName="dev",
        )
    except ClientError as e:
        logging.error(e)
    else:
        logger.info("API deployed successfully.")


def create_queue(
    queue_name, delay_seconds, visiblity_timeout, queue_arn, bucket_name, account_id
):
    """
    Create a standard SQS queue
    """
    sqs_resource = boto3.resource("sqs", region_name=AWS_REGION)

    role_policy = {
        "Version": "2012-10-17",
        "Id": "example-ID",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"Service": "s3.amazonaws.com"},
                "Action": ["SQS:SendMessage"],
                "Resource": queue_arn,
                "Condition": {
                    "ArnLike": {"aws:SourceArn": "arn:aws:s3:::" + bucket_name},
                    "StringEquals": {"aws:SourceAccount": account_id},
                },
            }
        ],
    }

    try:
        response = sqs_resource.create_queue(
            QueueName=queue_name,
            Attributes={
                "DelaySeconds": delay_seconds,
                "VisibilityTimeout": visiblity_timeout,
                "Policy": json.dumps(role_policy),
            },
        )
    except ClientError:
        logger.exception(f"Could not create SQS queue - {queue_name}.")
        raise
    else:
        logger.info(f"Queue {queue_name} created successfully.")
        return response


def upload_files(file_name, bucket, object_name=None, args=None):
    """
    Upload files to an S3 bucket
    """
    try:
        s3_client = boto3.client("s3", region_name=AWS_REGION)

        if object_name is None:
            object_name = file_name

        s3_client.upload_file(file_name, bucket, object_name, ExtraArgs=args)

    except ClientError:
        logger.exception(f"Could not upload files to - {bucket}.")

    else:
        logger.info(f"'{file_name}' has been uploaded to '{bucket}'")


def create_bucket_notification(queue_name, queue_arn, bucket_name):
    """
    Create event notification when an object is added to the S3 bucket
    """
    s3_client = boto3.client("s3", region_name=AWS_REGION)

    try:
        queue_name = queue_name
        queue_arn = queue_arn
        bucket = bucket_name
        prefix = "./files/"

        configurations = []

        # New configuration to add
        new_configuration = {
            "Id": f"Notif_{queue_name}",
            "QueueArn": queue_arn,
            "Events": [
                "s3:ObjectCreated:*",
            ],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {"Name": "prefix", "Value": prefix},
                    ]
                }
            },
        }

        configurations.append(new_configuration)

        response = s3_client.put_bucket_notification_configuration(
            Bucket=bucket,
            NotificationConfiguration={"QueueConfigurations": configurations},
        )

    except ClientError:
        logger.exception(f"Could not add event notification to - {bucket_name}.")
        raise
    else:
        logger.info("Bucket event notification has been added successfully.")
        return response


def demo():
    # CONSTANTS
    ACCOUNT_ID = get_account_id()
    QUEUE_NAME = "aclarion-queue"
    DELAY_SECONDS = "0"
    VISIBLITY_TIMEOUT = "60"
    QUEUE_ARN = "arn:aws:sqs:us-east-1:973861173512:aclarion-queue"
    S3_BUCKET_NAME = "aclarion-bucket-1"
    LAMBDA_FUNCTION_NAME = "aclarionLambdaFunction"

    logger.info("Creating an S3 bucket")
    create_bucket("aclarion-bucket-1")

    # logger.info('Fetching existing buckets')
    # fetch_buckets()

    logger.info("Creating SQS queue.")
    output = create_queue(
        QUEUE_NAME,
        DELAY_SECONDS,
        VISIBLITY_TIMEOUT,
        QUEUE_ARN,
        S3_BUCKET_NAME,
        ACCOUNT_ID,
    )
    QUEUE_URL = output.url
    logger.info(f"The queue URL is '{QUEUE_URL}'")

    logger.info("Creating bucket notification")
    create_bucket_notification(QUEUE_NAME, QUEUE_ARN, S3_BUCKET_NAME)

    logger.info("Uploading files to the S3 bucket")
    upload_files("./files/demo.png", S3_BUCKET_NAME)

    logger.info("Creating lambda execution role")
    # create_lambda_execution_role()
    ROLE = get_lambda_execution_role()

    # logger.info('Creating API execution role')
    # create_api_execution_role()
    # role = create_api_execution_role()

    logger.info("Creating lambda function.")
    LAMBDA_ARN = create_lambda_function(LAMBDA_FUNCTION_NAME, ROLE)

    logger.info("Creating REST API")
    REST_API_ID = create_rest_api("aclarionAPI")

    aws_lambda = boto3.client("lambda", region_name=AWS_REGION)

    LAMBDA_VERSION = aws_lambda.meta.service_model.api_version

    uri_data = {
        "aws-region": AWS_REGION,
        "api-version": LAMBDA_VERSION,
        "aws-acct-id": ACCOUNT_ID,
        "lambda-function-name": LAMBDA_FUNCTION_NAME,
        "aws-api-id": REST_API_ID,
    }

    logger.info("Adding lambda permission")
    add_lambda_permission(uri_data)

    logger.info("Getting API root ID.")
    API_ROOT_ID = get_api_root_id(REST_API_ID)

    logger.info("Creating REST API resource.")
    API_RESOURCE_ID = create_api_resource(
        REST_API_ID, API_ROOT_ID, LAMBDA_FUNCTION_NAME
    )

    logger.info("Creating REST API POST method.")
    create_post_method(REST_API_ID, API_RESOURCE_ID)

    logger.info("Deploying REST API in API Gateway..")
    deploy(REST_API_ID, API_RESOURCE_ID, LAMBDA_ARN)


def destroy(rest_api_id, lambda_function_name):
    """
    Destroys all the resources created
    :param rest_api_name: The name of the demo REST API.
    :param lambda_function_name: The name of the lambda function
    """
    api_client = boto3.client("apigateway")

    logger.info("Deleting REST API")

    try:
        response = api_client.delete_rest_api(restApiId=rest_api_id)

    except ClientError:
        logger.exception("Error deleting the REST API")
    else:
        logger.info("Successfully deleted REST API")

    lambda_client = boto3.client("lambda")

    logger.info("Deleting Lambda Function")

    try:
        response = lambda_client.delete_function(FunctionName=lambda_function_name)
    except ClientError:
        logger.exception("Error deleting the lambda function")
    else:
        logger.info("Successfully deleted lambda function")


########################################
# Main routine
########################################
def main():
    parser = argparse.ArgumentParser(
        description="Runs the Aclarion Proof of Concept Demo. Run this script with the "
        "'demo' flag to see example usage. Run with the 'destroy' flag to "
        "clean up all resources."
    )
    parser.add_argument(
        "action",
        choices=["demo", "destroy"],
        help="Indicates the action the script performs.",
    )
    args = parser.parse_args()

    print("-" * 88)
    print("Welcome to the Aclarion Proof of Concept Demo!")
    print("-" * 88)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.action == "demo":
        print("Deploying prerequisite resources for the demo.")
        demo()
    elif args.action == "destroy":
        print("Destroying AWS resources created for the demo.")
        destroy("zd4h1h28u5", "aclarionLambdaFunction")

    print("-" * 88)


if __name__ == "__main__":
    main()
