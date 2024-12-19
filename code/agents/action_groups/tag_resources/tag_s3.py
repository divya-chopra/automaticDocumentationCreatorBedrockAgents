import json
import boto3
from typing import Dict, Any

def add_tag_to_s3(bucket_name: str, tag_name: str, tag_value: str) -> Dict:
    """
    Add or update a tag to an S3 bucket
    
    Args:
        bucket_name (str): Name of the S3 bucket
        tag_name (str): Name of the tag to add/update
        tag_value (str): Value for the tag
    
    Returns:
        Dict: Result of the tagging operation with success status and message
    """
    try:
        s3 = boto3.client('s3')
        
        # Try to get existing tags, if any
        try:
            current_tags = s3.get_bucket_tagging(Bucket=bucket_name)
            tag_set = current_tags['TagSet']
        except s3.exceptions.ClientError:
            # Bucket has no tags yet
            tag_set = []

        # Remove existing tag if present and add new one
        new_tags = [tag for tag in tag_set if tag['Key'] != tag_name]
        new_tags.append({'Key': tag_name, 'Value': tag_value})

        # Update bucket tags
        s3.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={'TagSet': new_tags}
        )
        return {
            'success': True,
            'message': f'Successfully added tag {tag_name}={tag_value} to bucket {bucket_name}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error tagging S3 bucket: {str(e)}'
        }

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main handler function for adding tags to S3 buckets
    
    Expected event parameters:
    - tag_name: Name of the tag
    - tag_value: Value for the tag
    - bucket_name: Name of the S3 bucket to tag
    
    Returns:
        Dict: Response formatted for Bedrock Agent
    """
    try:
        # Log the incoming event for debugging
        print(f"Received event: {json.dumps(event)}")
        
        # Extract basic event information
        message_version = event.get('messageVersion', '1.0')
        
        # Extract parameters from the event
        parameters = event.get('parameters', [])
        tag_name = None
        tag_value = None
        bucket_name = None
        
        # Parse parameters
        for param in parameters:
            if param.get('name') == 'tag_name':
                tag_name = param.get('value')
            elif param.get('name') == 'tag_value':
                tag_value = param.get('value')
            elif param.get('name') == 'bucket_name':
                bucket_name = param.get('value')
        
        # Validate required parameters
        if not all([tag_name, tag_value, bucket_name]):
            missing_params = []
            if not tag_name:
                missing_params.append("tag_name")
            if not tag_value:
                missing_params.append("tag_value")
            if not bucket_name:
                missing_params.append("bucket_name")
                
            # Return error response if parameters are missing
            return {
                "messageVersion": message_version,
                "response": {
                    "actionGroup": event.get('actionGroup', ''),
                    "function": event.get('function', ''),
                    "functionResponse": {
                        "responseBody": {
                            "TEXT": {
                                "body": f"❌ Error: Missing required parameters: {', '.join(missing_params)}"
                            }
                        }
                    }
                }
            }

        # Add tag to the S3 bucket
        result = add_tag_to_s3(bucket_name, tag_name, tag_value)

        # Create response based on the result
        return {
            "messageVersion": message_version,
            "response": {
                "actionGroup": event.get('actionGroup', ''),
                "function": event.get('function', ''),
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": f"✅ {result['message']}" if result['success'] else f"❌ {result['message']}"
                        }
                    }
                }
            }
        }

    except Exception as e:
        # Handle any unexpected errors
        print(f"Error in lambda_handler: {str(e)}")
        return {
            "messageVersion": message_version,
            "response": {
                "actionGroup": event.get('actionGroup', ''),
                "function": event.get('function', ''),
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": f"❌ Error processing request: {str(e)}"
                        }
                    }
                }
            }
        }