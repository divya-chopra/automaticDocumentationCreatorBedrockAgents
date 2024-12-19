import json
import boto3
from datetime import datetime
from typing import Dict, Any

def get_infrastructure_details(app_id):
    """Fetch detailed infrastructure information and return in YAML format"""
    try:
        # Initialize AWS clients
        ec2 = boto3.client('ec2')
        dynamodb = boto3.client('dynamodb')
        s3 = boto3.client('s3')
        elbv2 = boto3.client('elbv2')
        iam = boto3.client('iam')
        lambda_client = boto3.client('lambda')
        apigw = boto3.client('apigateway')

        # Start YAML structure
        response_text = f"""# Infrastructure Documentation
metadata:
  app_id: {app_id}
  timestamp: {datetime.now().isoformat()}
  region: {boto3.session.Session().region_name}

resources:"""

        # Get Lambda functions
        try:
            functions = lambda_client.list_functions()['Functions']
            has_lambda = False
            lambda_text = """
  serverless:
    lambda_functions:"""
            
            for function in functions:
                tags = lambda_client.list_tags(Resource=function['FunctionArn'])['Tags']
                if tags.get('app_id') == app_id:
                    has_lambda = True
                    config = lambda_client.get_function_configuration(
                        FunctionName=function['FunctionName']
                    )
                    
                    lambda_text += f"""
      - function_name: {function['FunctionName']}
        runtime: {config['Runtime']}
        handler: {config['Handler']}
        memory: {config['MemorySize']} MB
        timeout: {config['Timeout']} seconds
        last_modified: {config['LastModified']}
        code_size: {config['CodeSize']} bytes
        """

                    try:
                        url_config = lambda_client.get_function_url_config(
                            FunctionName=function['FunctionName']
                        )
                        lambda_text += f"""
        function_url: {url_config['FunctionUrl']}"""
                    except:
                        pass
            
            if has_lambda:
                response_text += lambda_text

        except Exception as e:
            print(f"Error processing Lambda functions: {str(e)}")

        # Get API Gateway APIs
        try:
            apis = apigw.get_rest_apis()['items']
            has_api = False
            api_text = """
    api_gateway:
      rest_apis:"""
            
            for api in apis:
                tags = api.get('tags', {})
                if tags.get('app_id') == app_id:
                    has_api = True
                    resources = apigw.get_resources(restApiId=api['id'])['items']
                    
                    api_text += f"""
      - api_name: {api['name']}
        api_id: {api['id']}
        created_date: {api['createdDate'].isoformat()}
        endpoint_configuration: {api['endpointConfiguration']['types']}
        resources:"""
                    
                    for resource in resources:
                        api_text += f"""
          - path: {resource['path']}
            resource_id: {resource['id']}"""
                        
                        if 'resourceMethods' in resource:
                            api_text += """
            methods:"""
                            for method in resource['resourceMethods'].keys():
                                method_detail = apigw.get_method(
                                    restApiId=api['id'],
                                    resourceId=resource['id'],
                                    httpMethod=method
                                )
                                api_text += f"""
              - http_method: {method}
                authorization: {method_detail['authorizationType']}
                api_key_required: {method_detail['apiKeyRequired']}"""
                    
                    stages = apigw.get_stages(restApiId=api['id'])['item']
                    api_text += """
        stages:"""
                    for stage in stages:
                        api_text += f"""
          - stage_name: {stage['stageName']}
            deployment_id: {stage.get('deploymentId', 'N/A')}
            created_date: {stage.get('createdDate', 'N/A')}"""
            
            if has_api:
                response_text += api_text

        except Exception as e:
            print(f"Error processing API Gateway: {str(e)}")

        # Get EC2 instances
        try:
            instances = ec2.describe_instances(
                Filters=[{'Name': 'tag:app_id', 'Values': [app_id]}]
            )
            has_ec2 = False
            ec2_text = """
  compute:
    ec2_instances:"""

            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    has_ec2 = True
                    volumes = ec2.describe_volumes(
                        Filters=[{'Name': 'attachment.instance-id', 'Values': [instance['InstanceId']]}]
                    )['Volumes']
                    
                    ec2_text += f"""
      - instance_id: {instance['InstanceId']}
        instance_type: {instance['InstanceType']}
        state: {instance['State']['Name']}
        launch_time: {instance.get('LaunchTime', 'N/A').isoformat()}
        availability_zone: {instance.get('Placement', {}).get('AvailabilityZone', 'N/A')}
        vpc_id: {instance.get('VpcId', 'N/A')}
        subnet_id: {instance.get('SubnetId', 'N/A')}
        private_ip: {instance.get('PrivateIpAddress', 'N/A')}
        public_ip: {instance.get('PublicIpAddress', 'N/A')}
        platform: {instance.get('Platform', 'N/A')}
        architecture: {instance.get('Architecture', 'N/A')}
        root_device_type: {instance.get('RootDeviceType', 'N/A')}
        volumes:"""
                    
                    for volume in volumes:
                        ec2_text += f"""
          - volume_id: {volume['VolumeId']}
            size: {volume['Size']} GiB
            volume_type: {volume['VolumeType']}
            iops: {volume.get('Iops', 'N/A')} 
            encrypted: {volume['Encrypted']}"""
                    
                    ec2_text += """
        security_groups:"""
                    for sg in instance['SecurityGroups']:
                        sg_details = ec2.describe_security_groups(GroupIds=[sg['GroupId']])['SecurityGroups'][0]
                        ec2_text += f"""
          - group_id: {sg['GroupId']}
            group_name: {sg['GroupName']}
            inbound_rules:"""
                        for rule in sg_details['IpPermissions']:
                            ec2_text += f"""
              - protocol: {rule.get('IpProtocol', 'N/A')}
                from_port: {rule.get('FromPort', 'N/A')}
                to_port: {rule.get('ToPort', 'N/A')}
                sources: {[ip['CidrIp'] for ip in rule.get('IpRanges', [])]}"""
            
            if has_ec2:
                response_text += ec2_text

        except Exception as e:
            print(f"Error processing EC2 instances: {str(e)}")

        # Get DynamoDB tables
        try:
            tables = dynamodb.list_tables()['TableNames']
            has_tables = False
            dynamo_text = """
  database:
    dynamodb_tables:"""
            
            for table_name in tables:
                try:
                    table_arn = f"arn:aws:dynamodb:{dynamodb.meta.region_name}:{boto3.client('sts').get_caller_identity()['Account']}:table/{table_name}"
                    tags = dynamodb.list_tags_of_resource(ResourceArn=table_arn)['Tags']
                    if any(tag['Key'] == 'app_id' and tag['Value'] == app_id for tag in tags):
                        has_tables = True
                        table_info = dynamodb.describe_table(TableName=table_name)['Table']
                        dynamo_text += f"""
      - table_name: {table_name}
        status: {table_info['TableStatus']}
        creation_date: {table_info['CreationDateTime'].isoformat()}
        size_bytes: {table_info.get('TableSizeBytes', 0)}
        item_count: {table_info.get('ItemCount', 0)}
        billing_mode: {table_info.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')}"""
                        
                        if 'ProvisionedThroughput' in table_info:
                            dynamo_text += f"""
        provisioned_throughput:
          read_capacity_units: {table_info['ProvisionedThroughput']['ReadCapacityUnits']}
          write_capacity_units: {table_info['ProvisionedThroughput']['WriteCapacityUnits']}"""
                        
                        dynamo_text += f"""
        primary_key:
          hash_key: {table_info['KeySchema'][0]['AttributeName']}
          hash_key_type: {table_info['AttributeDefinitions'][0]['AttributeType']}"""
                except Exception as e:
                    print(f"Error processing DynamoDB table {table_name}: {str(e)}")
            
            if has_tables:
                response_text += dynamo_text

        except Exception as e:
            print(f"Error processing DynamoDB tables: {str(e)}")

        # Get S3 buckets
        try:
            buckets = s3.list_buckets()['Buckets']
            has_s3 = False
            s3_text = """
  storage:
    s3_buckets:"""
            
            for bucket in buckets:
                try:
                    tags = s3.get_bucket_tagging(Bucket=bucket['Name'])['TagSet']
                    if any(tag['Key'] == 'app_id' and tag['Value'] == app_id for tag in tags):
                        has_s3 = True
                        bucket_location = s3.get_bucket_location(Bucket=bucket['Name'])
                        versioning = s3.get_bucket_versioning(Bucket=bucket['Name'])
                        
                        s3_text += f"""
      - bucket_name: {bucket['Name']}
        creation_date: {bucket['CreationDate'].isoformat()}
        region: {bucket_location.get('LocationConstraint', 'us-east-1')}
        versioning: {versioning.get('Status', 'Disabled')}"""
                        
                        try:
                            bucket_encryption = s3.get_bucket_encryption(Bucket=bucket['Name'])
                            s3_text += f"""
        encryption:
          type: {bucket_encryption['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']}"""
                        except:
                            s3_text += """
        encryption: Not configured"""
                except Exception as e:
                    print(f"Error processing S3 bucket {bucket['Name']}: {str(e)}")
            
            if has_s3:
                response_text += s3_text

        except Exception as e:
            print(f"Error processing S3 buckets: {str(e)}")

        # Get Load Balancers
        try:
            load_balancers = elbv2.describe_load_balancers()['LoadBalancers']
            has_lb = False
            lb_text = """
  networking:
    load_balancers:"""
            
            for lb in load_balancers:
                try:
                    tags = elbv2.describe_tags(
                        ResourceArns=[lb['LoadBalancerArn']]
                    )['TagDescriptions'][0]['Tags']
                    
                    if any(tag['Key'] == 'app_id' and tag['Value'] == app_id for tag in tags):
                        has_lb = True
                        target_groups = elbv2.describe_target_groups(
                            LoadBalancerArn=lb['LoadBalancerArn']
                        )['TargetGroups']
                        
                        listeners = elbv2.describe_listeners(
                            LoadBalancerArn=lb['LoadBalancerArn']
                        )['Listeners']
                        
                        lb_text += f"""
      - name: {lb['LoadBalancerName']}
        dns_name: {lb['DNSName']}
        scheme: {lb['Scheme']}
        vpc_id: {lb['VpcId']}
        type: {lb['Type']}
        state: {lb['State']['Code']}
        target_groups:"""
                        for tg in target_groups:
                            lb_text += f"""
          - name: {tg['TargetGroupName']}
            protocol: {tg['Protocol']}
            port: {tg['Port']}
            target_type: {tg['TargetType']}
            health_check:
              protocol: {tg['HealthCheckProtocol']}
              port: {tg['HealthCheckPort']}
              path: {tg['HealthCheckPath']}
              interval: {tg['HealthCheckIntervalSeconds']}
              timeout: {tg['HealthCheckTimeoutSeconds']}"""
                        
                        lb_text += """
        listeners:"""
                        for listener in listeners:
                            lb_text += f"""
          - protocol: {listener['Protocol']}
            port: {listener['Port']}
            default_action: {listener['DefaultActions'][0]['Type']}"""
                except Exception as e:
                    print(f"Error processing Load Balancer {lb['LoadBalancerArn']}: {str(e)}")
            
            if has_lb:
                response_text += lb_text

        except Exception as e:
            print(f"Error processing Load Balancers: {str(e)}")

        return response_text

    except Exception as e:
        return f"Error analyzing infrastructure: {str(e)}"

def format_infrastructure_details(raw_details: str) -> str:
    """
    Format the raw infrastructure details into readable HTML
    """
    # Split the details into sections
    lines = raw_details.split()
    formatted_html = ""
    
    # Track current section
    current_section = ""
    
    for line in lines:
        if line.endswith(':'):
            # New section
            if current_section:
                formatted_html += "</div>\n"
            current_section = line[:-1]
            formatted_html += f'<div class="section"><h4>{current_section}</h4>\n'
            continue
            
        # Add the line content
        if ':' in line:
            key, value = line.split(':', 1)
            formatted_html += f'<div class="item"><span class="label">{key}:</span><span class="value">{value}</span></div>\n'
        else:
            formatted_html += f'<div class="item">{line}</div>\n'
    
    if current_section:
        formatted_html += "</div>\n"
        
    return formatted_html

def generate_and_publish_documentation(app_id: str) -> Dict[str, Any]:
    """
    Generate and publish infrastructure documentation with clean styling
    """
    try:
        # Get infrastructure details
        infra_details = get_infrastructure_details(app_id)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Infrastructure Documentation - App {app_id}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 40px;
                    line-height: 1.6;
                    color: #333;
                }}
                h1, h2, h3, h4 {{
                    color: #2c3e50;
                    margin-bottom: 10px;
                }}
                .label {{
                    font-weight: bold;
                    color: #2c3e50;
                    display: inline-block;
                    min-width: 150px;
                }}
                .value {{
                    display: inline-block;
                }}
                .item {{
                    margin: 5px 0;
                }}
                pre {{
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    font-family: monospace;
                    font-weight: bold;
                    padding: 20px;
                    border: 2px solid #3498db;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <h1>Infrastructure Documentation</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <h2>Application ID: {app_id}</h2>
            <pre>{infra_details}</pre>
        </body>
        </html>
        """

        # Upload to S3
        bucket_name = 'adc-knowledge-base-bucket'  # Replace with your bucket name
        file_name = f'infrastructure-doc-{app_id}-{datetime.now().strftime("%Y%m%d-%H%M%S")}.html'
        
        s3 = boto3.client('s3')
        s3.put_object(
            Bucket=bucket_name,
            Key=f'documentation/{file_name}',
            Body=html_content.encode('utf-8'),
            ContentType='text/html'
        )
        
        # Generate presigned URL (valid for 7 days)
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': f'documentation/{file_name}'},
            ExpiresIn=604800  # 7 days
        )
        
        return {
            'statusCode': 200,
            'documentation_url': url
        }
        
    except Exception as e:
        print(f"Error generating documentation: {str(e)}")
        return {
            'statusCode': 500,
            'error': f"Failed to generate documentation: {str(e)}"
        }

def create_response(message_version: str, action_group: str, function_name: str, response_body: Dict) -> Dict:
    """
    Helper function to create properly formatted response
    """
    action_response = {
        "actionGroup": action_group,
        "function": function_name,
        "functionResponse": {
            "responseBody": response_body
        }
    }
    
    api_response = {
        "messageVersion": message_version,
        "response": action_response
    }
    
    print("Response:")
    print(json.dumps(api_response))
    
    return api_response   

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main handler function for infrastructure details and documentation generation
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Extract function name and parameters
        function_name = event.get('function', '')
        actionGroup = event.get('actionGroup', '')
        message_version = event.get('messageVersion', '1.0')
        
        # Extract app_id from parameters array
        parameters = event.get('parameters', [])
        app_id = None
        for param in parameters:
            if param.get('name') == 'app_id':
                app_id = param.get('value')
                break
        
        # Validate app_id
        if not app_id:
            response_body = {
                "TEXT": {
                    "body": "❌ Error: app_id is required"
                }
            }
            return create_response(message_version, actionGroup, function_name, response_body)
            
        # Route to appropriate function based on function name
        if function_name == 'GetInfrastructureDetails':
            infrastructure_details = get_infrastructure_details(app_id)
            response_body = {
                "TEXT": {
                    "body": f"Infrastructure details for app_id {app_id}:\n{infrastructure_details}"
                }
            }
            return create_response(message_version, actionGroup, function_name, response_body)
            
        elif function_name == 'generate_and_publish_documentation':
            doc_response = generate_and_publish_documentation(app_id)
            if doc_response.get('statusCode') == 200:
                response_body = {
                    "TEXT": {
                        "body": f"✅ Documentation generated successfully!\nAccess it here: {doc_response.get('documentation_url')}"
                    }
                }
            else:
                response_body = {
                    "TEXT": {
                        "body": f"❌ Error generating documentation: {doc_response.get('error', 'Unknown error occurred')}"
                    }
                }
            return create_response(message_version, actionGroup, function_name, response_body)
                
        else:
            response_body = {
                "TEXT": {
                    "body": f"❌ Invalid function: {function_name}. Supported functions are: GetInfrastructureDetails, generate_and_publish_documentation"
                }
            }
            return create_response(message_version, actionGroup, function_name, response_body)
            
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        error_response = {
            "messageVersion": event.get("messageVersion", "1.0"),
            "response": {
                "actionGroup": event.get("actionGroup"),
                "function": event.get("function"),
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": f"❌ Error processing request: {str(e)}"
                        }
                    }
                }
            }
        }
        return error_response

