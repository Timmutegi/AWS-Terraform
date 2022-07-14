terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 0.14.9"
}

provider "aws" {
  # profile = "default"
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
  region     = var.region
}

resource "aws_s3_bucket" "s3_bucket" {
  bucket = var.bucket_name
}

resource "aws_iam_role" "iam_for_lambda" {
  name               = "iam_for_lambda"
  assume_role_policy = file("./aws_lambda.iam")
}

# Create Policy for IAM Role
resource "aws_iam_policy" "policy" {
  name        = "lambda_policy"
  description = "A test policy"
  policy      = file("./bucket_policy.iam")
}

resource "aws_iam_role_policy_attachment" "test-attach" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = aws_iam_policy.policy.arn
}

data "archive_file" "lambda_function_code" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_function/"
  output_path = "${path.module}/lambda_function/hello-python.zip"
}

resource "aws_lambda_function" "lambda_function" {
  # If the file is not in the current working directory you will need to include a 
  # path.module in the filename.
  filename      = "${path.module}/lambda_function/hello-python.zip"
  function_name = var.lambda_function_name
  role          = aws_iam_role.iam_for_lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.9"
}

resource "aws_api_gateway_rest_api" "rest_api" {
  name        = var.rest_api_name
  description = "This API is an event source for the lambda function"
}

resource "aws_api_gateway_resource" "file_resource" {
  parent_id   = aws_api_gateway_rest_api.rest_api.root_resource_id
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  path_part   = "{${var.resource_name}+}"
}

resource "aws_api_gateway_method" "file_method" {
  rest_api_id   = aws_api_gateway_rest_api.rest_api.id
  resource_id   = aws_api_gateway_resource.file_resource.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambdapy" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  resource_id = aws_api_gateway_method.file_method.resource_id
  http_method = aws_api_gateway_method.file_method.http_method

  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = aws_lambda_function.lambda_function.invoke_arn
  passthrough_behavior    = "WHEN_NO_TEMPLATES"

  request_templates = {
    "application/json" = <<EOF
    {
      "url" : $util.urlDecode($input.params('url'))
    }
    EOF
  }
}

resource "aws_api_gateway_method" "file_rootpy" {
  rest_api_id   = aws_api_gateway_rest_api.rest_api.id
  resource_id   = aws_api_gateway_rest_api.rest_api.root_resource_id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_rootpy" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  resource_id = aws_api_gateway_method.file_rootpy.resource_id
  http_method = aws_api_gateway_method.file_rootpy.http_method

  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = aws_lambda_function.lambda_function.invoke_arn
}

resource "aws_api_gateway_method_response" "response_200" {
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  resource_id = aws_api_gateway_resource.file_resource.id
  http_method = aws_api_gateway_method.file_method.http_method
  status_code = "200"

  response_models = { "application/json" = "Empty" }
}

resource "aws_api_gateway_integration_response" "IntegrationResponse" {
  depends_on = [
    aws_api_gateway_integration.lambdapy,
    aws_api_gateway_integration.lambda_rootpy,
  ]
  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  resource_id = aws_api_gateway_resource.file_resource.id
  http_method = aws_api_gateway_method.file_method.http_method
  status_code = aws_api_gateway_method_response.response_200.status_code
  # Transforms the backend JSON response to json. The space is "A must have"
  response_templates = {
    "application/json" = <<EOF
  EOF
  }
}

resource "aws_api_gateway_deployment" "gateway_deployment" {
  depends_on = [
    aws_api_gateway_integration.lambdapy,
    aws_api_gateway_integration_response.IntegrationResponse,
  ]

  rest_api_id = aws_api_gateway_rest_api.rest_api.id
  stage_name  = var.stage

}

resource "aws_lambda_permission" "lambda_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_function.function_name
  principal     = "apigateway.amazonaws.com"

  # The /*/* portion grants access from any method on any resource
  # within the API Gateway "REST API".
  source_arn = "${aws_api_gateway_rest_api.rest_api.execution_arn}/*/*"
}

resource "aws_sqs_queue" "queue" {
  name   = "s3-event-notification-queue"
  policy = file("./sqs_policy.iam")
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket     = aws_s3_bucket.s3_bucket.id
  depends_on = [aws_sqs_queue.queue]

  queue {
    id            = aws_sqs_queue.queue.id
    queue_arn     = aws_sqs_queue.queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_suffix = ".log"
  }
}
