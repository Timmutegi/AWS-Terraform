variable "region" {
  type    = string
  default = "us-east-1"
}

variable "resource_name" {
  type    = string
  default = "file"
}

variable "stage" {
  type    = string
  default = "dev"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the lambda function"
  default     = "my_lambda_function"
}

variable "rest_api_name" {
  type        = string
  description = "Name of the REST API"
  default     = "my_rest_api"
}

variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket"
  default     = "tesh-mutegi-bucket"
}

#AWS authentication variables
variable "aws_access_key" {
  type        = string
  description = "AWS Access Key"
}

variable "aws_secret_key" {
  type        = string
  description = "AWS Secret Key"
}