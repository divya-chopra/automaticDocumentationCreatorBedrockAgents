# # lambda.tf

# # Create ZIP file for Lambda deployment
# data "archive_file" "lambda_zip" {
#   type        = "zip"
#   source_file = "${path.module}/agents/infrastructure_analyzer.py"
#   output_path = "${path.module}/infrastructure_analyzer.zip"
# }

# # IAM role for Lambda
# resource "aws_iam_role" "lambda_role" {
#   name = "infrastructure_analyzer_role"

#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Action = "sts:AssumeRole"
#         Effect = "Allow"
#         Principal = {
#           Service = "lambda.amazonaws.com"
#         }
#       }
#     ]
#   })
# }

# # IAM policy for the Lambda role
# resource "aws_iam_role_policy" "lambda_policy" {
#   name = "infrastructure_analyzer_policy"
#   role = aws_iam_role.lambda_role.id

#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Effect = "Allow"
#         Action = [
#           "ec2:DescribeInstances",
#           "dynamodb:ListTables",
#           "dynamodb:DescribeTable",
#           "dynamodb:ListTagsOfResource",
#           "s3:ListBuckets",
#           "s3:GetBucketTagging",
#           "elasticloadbalancing:DescribeLoadBalancers",
#           "elasticloadbalancing:DescribeTags",
#           "elasticloadbalancing:DescribeTargetGroups"
#         ]
#         Resource = "*"
#       },
#       {
#         Effect = "Allow"
#         Action = [
#           "logs:CreateLogGroup",
#           "logs:CreateLogStream",
#           "logs:PutLogEvents"
#         ]
#         Resource = "arn:aws:logs:*:*:*"
#       }
#     ]
#   })
# }

# # Lambda function
# resource "aws_lambda_function" "infrastructure_analyzer" {
#   filename         = data.archive_file.lambda_zip.output_path
#   function_name    = "infrastructure_analyzer"
#   role            = aws_iam_role.lambda_role.arn
#   handler         = "lambda_function.lambda_handler"
#   source_code_hash = data.archive_file.lambda_zip.output_base64sha256
#   runtime         = "python3.9"
#   timeout         = 30
#   memory_size     = 256

#   environment {
#     variables = {
#       ENVIRONMENT = "production"
#     }
#   }

#   tags = {
#     Name    = "infrastructureanalyzer"
#     app_id  = "100"
#   }
# }

# # CloudWatch Log Group
# resource "aws_cloudwatch_log_group" "lambda_logs" {
#   name              = "/aws/lambda/infrastructure-analyzer"
#   retention_in_days = 14
# }

# # Outputs
# output "lambda_function_arn" {
#   description = "The ARN of the Lambda function"
#   value       = aws_lambda_function.infrastructure_analyzer.arn
# }

# output "lambda_function_name" {
#   description = "The name of the Lambda function"
#   value       = aws_lambda_function.infrastructure_analyzer.function_name
# }