# Configure AWS Provider
provider "aws" {
  region = "us-east-1"
}

# Lambda IAM Role
resource "aws_iam_role" "lambda_role" {
  name = "simple_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    app_id = "101"
  }
}

# IAM policy for Lambda to access DynamoDB and CloudWatch Logs
resource "aws_iam_role_policy" "lambda_policy" {
  name = "simple_lambda_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Scan"
        ]
        Resource = [aws_dynamodb_table.simple_table.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = ["arn:aws:logs:*:*:*"]
      }
    ]
  })
}

# DynamoDB Table
resource "aws_dynamodb_table" "simple_table" {
  name           = "simple-serverless-table"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"
  
  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    app_id = "101"
  }
}

# Lambda Function with inline code
resource "aws_lambda_function" "simple_lambda" {
  filename      = "dummy.zip"  # Required but not used for inline code
  function_name = "simple-serverless-function"
  role         = aws_iam_role.lambda_role.arn
  handler      = "index.handler"
  runtime      = "nodejs18.x"

  # Inline Lambda function code
  source_code_hash = base64sha256("dummy")  # Required but not used for inline code
  
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.simple_table.name
    }
  }

  tags = {
    app_id = "101"
  }
}

# Create a dummy zip file for Lambda
data "archive_file" "dummy" {
  type        = "zip"
  output_path = "dummy.zip"

  source {
    content  = <<EOF
exports.handler = async (event) => {
    try {
        // Parse the incoming request body
        const body = event.body ? JSON.parse(event.body) : {};
        
        // Get name from request or use default
        const name = body.name || "World";
        
        // Create response
        const response = {
            message: `Hello,`,
            timestamp: new Date().toISOString(),
            requestDetails: {
                method: event.httpMethod,
                path: event.path,
                queryStringParameters: event.queryStringParameters
            }
        };
        
        // Return successful response
        return {
            statusCode: 200,
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            body: JSON.stringify(response)
        };
    } catch (error) {
        // Return error response if something goes wrong
        return {
            statusCode: 500,
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            body: JSON.stringify({
                message: "Error processing request",
                error: error.message
            })
        };
    }
};
EOF
    filename = "index.js"
  }
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "simple_api" {
  name = "simple-serverless-api"

  tags = {
    app_id = "101"
  }
}

# API Gateway Resource
resource "aws_api_gateway_resource" "simple_resource" {
  rest_api_id = aws_api_gateway_rest_api.simple_api.id
  parent_id   = aws_api_gateway_rest_api.simple_api.root_resource_id
  path_part   = "items"
}

# API Gateway Method
resource "aws_api_gateway_method" "simple_method" {
  rest_api_id   = aws_api_gateway_rest_api.simple_api.id
  resource_id   = aws_api_gateway_resource.simple_resource.id
  http_method   = "POST"
  authorization = "NONE"
}

# API Gateway Integration
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.simple_api.id
  resource_id = aws_api_gateway_resource.simple_resource.id
  http_method = aws_api_gateway_method.simple_method.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.simple_lambda.invoke_arn
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.simple_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.simple_api.execution_arn}/*/*"
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "simple_deployment" {
  depends_on = [aws_api_gateway_integration.lambda_integration]
  
  rest_api_id = aws_api_gateway_rest_api.simple_api.id
  
  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "simple_stage" {
  deployment_id = aws_api_gateway_deployment.simple_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.simple_api.id
  stage_name    = "prod"

  tags = {
    app_id = "101"
  }
}

# Output the API Gateway URL
output "api_url" {
  value = "${aws_api_gateway_stage.simple_stage.invoke_url}/items"
}