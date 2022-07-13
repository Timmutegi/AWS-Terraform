variable "region" {
  type    = string
  default = "us-west-1"
}

variable "resource_name" {
  type    = string
  default = "file"
}

variable "stage" {
  type    = string
  default = "dev"
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