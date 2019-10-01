#!/usr/bin/env python3
import boto3
import logging


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


# Assume the role of a connected account
def assume_role(AccountID, STSRole, SessionID):
    print(f'ATTEMPTING TO CHECK ACCOUNT ID# {AccountID}')
    credentials = {}
    try:
        arn = f'arn:aws:iam::{AccountID}:role/{STSRole}'
        client = boto3.client('sts')

        response = client.assume_role(RoleArn=arn, RoleSessionName=SessionID)

        # Parse the assume_role() response for the needed creds
        credentials = {
            'aki': response['Credentials']['AccessKeyId'],
            'sak': response['Credentials']['SecretAccessKey'],
            'token': response['Credentials']['SessionToken']
            }

        log.info(f'SUCCESSFULLY CONNECTED TO ACCOUNT ID {AccountID}')
        # print(f'CREDS: {credentials}')
        return(credentials)

    except Exception as e:
        log.error(f'PROBLEM CONNECTING TO ACCOUNT {AccountID} :\n{e}')
        raise e
        return(False)


# Get a list of running EC2 instances, using creds passed for client connection
def list_ec2_instances(region, credentials):
    OnInstances = []
    ec2 = boto3.client(
            'ec2',
            region_name=region,
            aws_access_key_id=credentials['aki'],
            aws_secret_access_key=credentials['sak'],
            aws_session_token=credentials['token']
        )

    response = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            OnInstances.append(instance['InstanceId'])

    return(OnInstances)


# Main function
def lambda_handler(event, context):

    # All of the child accounts we're connecting to
    AWSChildAccounts = [
        # your aws account numbers
        '1234567890',
        '0987654321'
    ]

    # get the region this script is running from, to target on child accounts
    region = boto3.session.Session().region_name

    # IAM Role that the  master account has access to assume
    RoleName = 'IAM-ROLE-NAME'

    # Identifier that will tail the end of the above role when executiting
    STSSessionID = 'NAME-OF-THIS-PROGRAM'

    # Cycle accounts, assuming the role and running a function with creds
    for account in AWSChildAccounts:
        try:
            creds = assume_role(account, RoleName, STSSessionID)

            print(f'\nACCOUNT: {account} \n RUNNING INSTANCES: ')
            print('\t' + '\n\t'.join(list_ec2_instances(region, creds)))

        except exception as E:
            log.error(f'CAN\'T ACCECCESS ACCOUNT#: {account} DUE TO:\n{e}')


# Run main on load if running from the command line
if __name__ == "__main__":
    lambda_handler('{}', '')
