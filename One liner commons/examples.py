'''
Python3 w/Boto3
'''

# AWS account ID
MyAWSAccount = boto3.client('sts').get_caller_identity().get('Account')

# AWS Account names
MyAWSAccountName = ' '.join([i['AccountAliases'] for i in boto3.client('iam').get_paginator('list_account_aliases').paginate()][0])

# All IAM users
AllUsers = boto3.client('iam').list_users()['Users']

# A list of all running EC2 Instances IDs
AllRunningEC2Instances = [i.id for i in boto3.resource('ec2').instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])]

# Lambda Function Name
AppName = context.function_name

# Lambda Function ARN
AppARN = context.invoked_function_arn

# Lambda Function Log Stream Name
LogStream = context.log_stream_name

# Lambda Function Log Group
LogGroup = context.log_group_name
