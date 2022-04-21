# AWS Serverless Example
- This repository shows an example of how AWS can be used to implement an event-driven architecture

## How it works
- This example uses a lambda function that is fronted by a REST API that accepts a url to a downloadable file as a query parameter.
- The lambda function is invoked by the API Gateway REST API and downloads the file from the URL then uploads it to an S3 bucket.
- The bucket is configured to send an event notification to an SQS queue when an object is uploaded.

## Technologies used
- Python
- AWS SDK
- Terraform

## AWS services used
1. AWS Lambda
2. API gateway
3. AWS S3
4. AWS SQS

## How to run
- Before you run the steps below, make sure Terraform is installed
1. Navigate to the `iac` directory
2. Assign your AWS Access Key obtained from your account to the **aws_access_key** variable
3. Assign your AWS AWS Secret Key obtained from your account to the **aws_secret_key** variable
4. Run `terraform init`
5. Run `terraform apply`
6. Copy the base URL displayed in the terminal
7. Open a browser and add a query parameter i.e. `https://36r9oe8n50.execute-api.us-west-1.amazonaws.com/dev/file?url=%22https://www.facebook.com/favicon.ico%22`
6. To destroy the resources, run `terraform destroy`
https://36r9oe8n50.execute-api.us-west-1.amazonaws.com/dev/file