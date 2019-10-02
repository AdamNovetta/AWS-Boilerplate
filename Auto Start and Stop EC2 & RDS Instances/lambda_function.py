#!/usr/bin/env python3
import boto3
import datetime
import json
import logging
import os
import time


# Output logging - default WARNING. Set to INFO for full output in cloudwatch
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# AWS Tags to target for starting and stopping
if os.environ['START_TAG']:
    start = os.environ['START_TAG']
else:
    start = 'autoOrc-up'
if os.environ['STOP_TAG']:
    stop = os.environ['STOP_TAG']
else:
    stop = 'autoOrc-down'

# Start instances only on weekdays? (change to False to start every day)
if os.environ['ONLY_START_WEEKDAYS']:
    weekdays = os.environ['ONLY_START_WEEKDAYS']
else:
    weekdays = True


# Main function that lambda calls
def lambda_handler(event, context):
    ThisLambda = context.function_name

    # Create cloudwatch metrics for instance start/stop/failure
    def put_cloudwatch_metric(MetricName, value, process, outcome):
        cw.put_metric_data(
            Namespace=f'{ThisLambda}-Results',
            MetricData=[{
                'MetricName': MetricName,
                'Value': value,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Process', 'Value': process},
                    {'Name': 'Outcome', 'Value': outcome}
                ]
            }]
        )

    # Get all available AWS regions
    def get_ec2_regions():
        session = boto3.session.Session()
        return(session.get_available_regions('ec2'))

    StartTag = 'tag:' + start
    StopTag = 'tag:' + stop
    aws_id = boto3.client('sts').get_caller_identity().get('Account')

    # Check to see if today is a weekday
    def weekday(test_date):
        if test_date.isoweekday() in range(1, 6):
            return(True)
        else:
            return(False)

    is_weekday = weekday(datetime.datetime.now())

    # Define a timer, used to gague shutdown time, in UTC
    timer = time.strftime("%H:%M")

    # Set base filters for running/stopped instances, and matching orc tags
    FilterRunning = [
        {'Name': 'instance-state-name', 'Values': ['running']},
        {'Name': StopTag, 'Values': [timer]}
        ]

    FilterStopped = [
        {'Name': 'instance-state-name', 'Values': ['stopped']},
        {'Name': StartTag, 'Values': [timer]}
        ]

    counter = 0
    ErrorCounter = 0

    # On initial lambda run, spawn regional AutoOrcs
    if 'REGION_NAME' not in event.keys():
        ThisRegion = boto3.session.Session().region_name
        log.info(f'\n[ {ThisLambda} initializing at {timer} in {ThisRegion}]')
        for region in get_ec2_regions():
            resource = f'arn:aws:lambda:{ThisRegion}:{aws_id}:{ThisLambda}'
            try:
                resp = boto3.client('lambda').invoke(
                    FunctionName=resource,
                    InvocationType='Event',
                    Payload=json.dumps({'REGION_NAME': region})
                )
                response = True
                log.info(f'Invoking {ThisLambda} targeting {region} region')

            except Exception as e:
                log.error(f'FAILED Invoking {ThisLambda} in {region} - {e}')

    # If spawned from inital Lambda run, connect to the passed REGION_NAME
    else:
        # Define boto3 connections/variables ##################################
        region = event['REGION_NAME']
        log.info(f'\n[ {ThisLambda} start time : {timer} in {region} ]')
        LocalSession = boto3.session.Session(region_name=region)
        cw = LocalSession.client('cloudwatch')
        rds = LocalSession.client('rds')
        ec2 = LocalSession.resource('ec2')
        # #####################################################################

        # Find the name tag of an instance
        def get_ec2_instance_name(InstID):
            InstName = None
            unnamed_label = '(no \'name\' Tag)'
            EC2Inst = ec2.Instance(InstID)
            if EC2Inst.tags is not None:
                for tags in EC2Inst.tags:
                    if tags['Key'] == 'Name':
                        InstName = tags["Value"]
            if InstName is None or InstName == '':
                InstName = unnamed_label
            return(instance_name)

        # Get AutoOrc-down / AutoOrc-up tags on RDS instances
        def get_rds_orc_tags(ARN, phase):
            orc_timer = ''
            tags = rds.list_tags_for_resource(ResourceName=ARN)

            for tag in tags['TagList']:
                if tag['Key'] == phase:
                    orc_timer = tag['Value']

            return orc_timer

        # Find and shutdown matching EC2 instances
        try:
            OrcInstDown = ec2.instances.filter(Filters=FilterRunning)
            for instance in OrcInstDown:
                counter += 1
                StateCode = 0
                name = get_ec2_instance_name(instance.id)
                log.info(f' - Stopping Instance-ID: {instance.id} Name : {name}')
                resp = instance.stop()
                StateCode = resp['StoppingInstances'][0]['CurrentState']['Code']

                if StateCode == 16:
                    ErrorCounter += 1
                    log.error(f'ErrorCode # {StateCode} stopping: {name}')

            if (counter > 0):
                put_cloudwatch_metric(aws_id, counter, stop, 'Success')

            if (ErrorCounter > 0):
                put_cloudwatch_metric(aws_id, error_counter, stop, 'Error')
                log.error(f'x - Errors stopping {error_counter} instances')

            log.info(f'\t[ Stopped {counter} instances in {region} ]')
        except Exception as e:
            log.error(f'Unable to stop instance in {region} due to:\n{e}')

        # Find and start matching EC2 instances
        try:
            OrcInstUp = ec2.instances.filter(Filters=FilterStopped)
            counter = 0
            ErrorCounter = 0
            BadStartCodes = ['32', '48', '64', '80']

            # Cycle through and start tagged EC2 instances
            if is_weekday or weekdays is False:
                for instance in OrcInstUp:
                    counter += 1
                    StateCode = 0
                    name = get_ec2_instance_name(instance.id)
                    log.info(f'- Start Instance-ID: {instance.id}  Name: {name}')
                    resp = instance.start()
                    StateCode = resp['StartingInstances'][0]['CurrentState']['Code']

                    if StateCode in BadStartCodes:
                        ErrorCounter += 1
                        log.error(f'ErrorCode # {StateCode} starting: {name}')

                if (counter > 0):
                    put_cloudwatch_metric(aws_id, counter, start, 'Success')

                if (ErrorCounter > 0):
                    put_cloudwatch_metric(aws_id, error_counter, start, 'Error')
                    log.error(f'x - Errors starting {error_counter} instances')

            log.info(f'\t[ Started {counter} instances in {region} ]')
        except Exception as e:
            log.error(f'Unable to start instance in {region} due to:\n{e}')
        # Cycle through all RDS instaces, starting/stopping Orc tagged ones
        try:
            OrcRDS = rds.describe_db_instances()
            counter = 0
            for rds_inst in OrcRDS['DBInstances']:
                rds_name = str(rds_inst['DBInstanceIdentifier'])
                rds_arn = str(rds_inst['DBInstanceArn'])
                rds_status = str(rds_inst['DBInstanceStatus'])
                rds_az_state = str(rds_inst['MultiAZ'])

                if is_weekday or weekdays is False:

                    if rds_az_state == 'False' and rds_status == 'stopped':
                        orc_up = get_rds_orc_tags(rds_arn, start)

                        if orc_up == timer:
                            log.info(f'RDS : {rds_name} database is starting up')
                            rds.start_db_instance(DBInstanceIdentifier=rds_name)
                            counter += 1

                if rds_az_state == 'False' and rds_status == 'available':
                    orc_down = get_rds_orc_tags(rds_arn, stop)

                    if orc_down == timer:
                        log.info(f'RDS: {rds_name} is shutting down now')
                        rds.stop_db_instance(DBInstanceIdentifier=rds_name)
                        counter += 1
            log.info(f'\t[ Started & Stopped {counter} RDS DBs in {region} ]')
        except Exception as e:
            log.error(f'Unable to start/stop RDS in {region} due to:\n{e}')
        log.info(f'[ {ThisLambda} finished in {region} ]\n')
