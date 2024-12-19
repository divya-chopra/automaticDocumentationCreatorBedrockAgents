terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # Specify the AWS provider version you want to use
    }
  }
}

provider "aws" {
  region = var.region

  # The credentials will be loaded from environment variables:
  # AWS_ACCESS_KEY_ID
  # AWS_SECRET_ACCESS_KEY
  # AWS_REGION (optional, as we're setting it in the provider)
}