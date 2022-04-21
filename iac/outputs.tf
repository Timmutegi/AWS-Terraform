output "base_url" {
  value = "${aws_api_gateway_deployment.gateway_deployment.invoke_url}/${var.resource_name}"
}

output "bucket_name" {
  value = "${aws_s3_bucket.bucket.id}"
}