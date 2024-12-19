variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "demo-app"
}

variable "app_id" {
  description = "Application ID for resource tagging"
  type        = string
  default     = "100"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID where resources will be created"
  type        = string
  default = "vpc-0a617d92f82f7efd1"
  # You'll need to provide this value
}