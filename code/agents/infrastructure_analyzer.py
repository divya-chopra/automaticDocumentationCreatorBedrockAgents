import boto3
import json
from datetime import datetime
from typing import Dict, Any

class InfrastructureAnalyzer:
    def __init__(self):
        self.ec2_client = boto3.client('ec2')
        self.dynamodb_client = boto3.client('dynamodb')
        self.s3_client = boto3.client('s3')
        self.elbv2_client = boto3.client('elbv2')

    def analyze_infrastructure(self, app_id: str) -> Dict[str, Any]:
        try:
            analysis_result = {
                "requestTime": datetime.now().isoformat(),
                "appId": app_id,
                "infrastructure": {
                    "compute": self._get_ec2_resources(app_id),
                    "database": self._get_database_resources(app_id),
                    "storage": self._get_storage_resources(app_id),
                    "networking": self._get_networking_resources(app_id)
                }
            }
            return {
                "statusCode": 200,
                "body": json.dumps(analysis_result, default=str)
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": str(e),
                    "message": "Error analyzing infrastructure"
                })
            }

    def _get_ec2_resources(self, app_id: str) -> Dict:
        instances = self.ec2_client.describe_instances(
            Filters=[{'Name': 'tag:app_id', 'Values': [app_id]}]
        )
        
        ec2_resources = []
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                ec2_resources.append({
                    "instanceId": instance['InstanceId'],
                    "instanceType": instance['InstanceType'],
                    "state": instance['State']['Name'],
                    "privateIp": instance.get('PrivateIpAddress'),
                    "publicIp": instance.get('PublicIpAddress'),
                    "securityGroups": instance['SecurityGroups']
                })
        return {"instances": ec2_resources}

    def _get_database_resources(self, app_id: str) -> Dict:
        tables = self.dynamodb_client.list_tables()['TableNames']
        dynamodb_resources = []
        
        for table_name in tables:
            try:
                tags = self.dynamodb_client.list_tags_of_resource(
                    ResourceArn=f"arn:aws:dynamodb:{self.dynamodb_client.meta.region_name}:"
                              f"{boto3.client('sts').get_caller_identity()['Account']}:table/{table_name}"
                )['Tags']
                
                if any(tag['Key'] == 'app_id' and tag['Value'] == app_id for tag in tags):
                    table_info = self.dynamodb_client.describe_table(TableName=table_name)['Table']
                    dynamodb_resources.append({
                        "tableName": table_name,
                        "status": table_info['TableStatus'],
                        "readCapacity": table_info.get('ProvisionedThroughput', {}).get('ReadCapacityUnits'),
                        "writeCapacity": table_info.get('ProvisionedThroughput', {}).get('WriteCapacityUnits')
                    })
            except Exception as e:
                print(f"Error processing table {table_name}: {str(e)}")
                
        return {"dynamodbTables": dynamodb_resources}

    def _get_storage_resources(self, app_id: str) -> Dict:
        buckets = []
        for bucket in self.s3_client.list_buckets()['Buckets']:
            try:
                tags = self.s3_client.get_bucket_tagging(Bucket=bucket['Name'])['TagSet']
                if any(tag['Key'] == 'app_id' and tag['Value'] == app_id for tag in tags):
                    buckets.append({
                        "bucketName": bucket['Name'],
                        "creationDate": bucket['CreationDate'].isoformat()
                    })
            except Exception:
                continue
        return {"s3Buckets": buckets}

    def _get_networking_resources(self, app_id: str) -> Dict:
        load_balancers = []
        lbs = self.elbv2_client.describe_load_balancers()['LoadBalancers']
        
        for lb in lbs:
            tags = self.elbv2_client.describe_tags(
                ResourceArns=[lb['LoadBalancerArn']]
            )['TagDescriptions'][0]['Tags']
            
            if any(tag['Key'] == 'app_id' and tag['Value'] == app_id for tag in tags):
                target_groups = self.elbv2_client.describe_target_groups(
                    LoadBalancerArn=lb['LoadBalancerArn']
                )['TargetGroups']
                
                load_balancers.append({
                    "name": lb['LoadBalancerName'],
                    "dnsName": lb['DNSName'],
                    "scheme": lb['Scheme'],
                    "targetGroups": [{
                        "name": tg['TargetGroupName'],
                        "port": tg['Port'],
                        "protocol": tg['Protocol']
                    } for tg in target_groups]
                })
                
        return {"loadBalancers": load_balancers}

def lambda_handler(event, context):
    """Main Lambda handler function"""
    try:
        # Extract app_id from the event
        app_id = event.get('app_id')
        if not app_id:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Missing app_id parameter"
                })
            }
            
        analyzer = InfrastructureAnalyzer()
        return analyzer.analyze_infrastructure(app_id)
        
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "Internal server error"
            })
        }