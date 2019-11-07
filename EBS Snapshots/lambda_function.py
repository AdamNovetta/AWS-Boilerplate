#!/usr/bin/env python3
import boto3
import calendar
import os
import sys
import logging
import time
from datetime import datetime
from collections import OrderedDict

# Output logging - Set to INFO for full output in cloudwatch
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


# Main function
def lambda_handler(event, context):
    # Define boto3 connections/variables
    ec2 = boto3.resource('ec2')
    ec2Client = boto3.client('ec2')
    iam = boto3.client('iam')
    snsClient = boto3.client('sns')
    ThisRegion = boto3.session.Session().region_name
    # Meta variables for program operation
    AWSID = boto3.client('sts').get_caller_identity().get('Account')
    AccountNameList = iam.get_paginator('list_account_aliases').paginate()
    AccountName = ''.join([i['AccountAliases'] for i in AccountNameList][0])
    # Set the SNS Topic name either by environment variable or staticly here
    try:
        TopicName = os.environ['SNS_TOPIC']
    except Exception:
        TopicName = 'auto-snapshots'
    SNSARN = f'arn:aws:sns:{ThisRegion}:{AWSID}:{TopicName}'
    # Tags to append to EBS snapshots
    VolTags = ['DailySnapshot', 'WeeklySnapshot', 'MonthlySnapshot']
    # Placeholders for outputs
    DeleteList = []
    message = ''
    errmsg = ''
    # Counters for successful/failed operations
    TCreated = 0
    TDeleted = 0
    CountErr = 0
    CountSuccess = 0
    CountTotal = 0
    # Number of copies to keep snapshot types
    KeepWeek = 3
    KeepDay = 5
    KeepMonth = 2
    # Date/Time variables
    today = datetime.today()
    day = today.strftime('%-d')
    month = today.strftime('%-m')
    now = datetime.weekday(today)
    DaysInMonth = calendar.mdays[int(month)]
    tasks = VolTags

    # get the 'Name' tag out of the batch of tags sent
    def get_tag_name(AllTags):
        NameTag = ''
        if AllTags is not None:
            for tags in AllTags:
                if tags["Key"] == 'Name':
                    NameTag = tags["Value"]
        else:
            NameTag = "[ no name ]"
        return NameTag

    # Get the tags of a reouse that's passed to the func
    def get_resource_tags(resources):
        ResourceID = resources.id
        ResourceTags = {}
        if ResourceID:
            TagFilter = [{
                'Name': 'resource-id',
                'Values': [ResourceID]
            }]
            tags = ec2Client.describe_tags(Filters=TagFilter)
            for tag in tags['Tags']:
                key = tag['Key']
                value = tag['Value']
                # Tags starting with 'aws:' are reserved for internal use
                # also don't double-tag snapshots with the scripts VolTags
                if not key.startswith('aws:') and str(key) not in str(VolTags):
                    ResourceTags[key] = value
        return(ResourceTags)

    # Set the tags of the resource from the tags passed to the function
    def set_resource_tags(resource, tags):
        for TKey, TValue in tags.items():
            if resource.tags is None:
                log.info(f' - Tagging {resource.id} with {TKey}:{TValue}')
                resource.create_tags(Tags=[{'Key': TKey, 'Value': TValue}])
            elif TKey not in resource.tags or resource.tags[TKey] is not TValue:
                log.info(f' - Tagging {resource.id} with {TKey}:{TValue}')
                resource.create_tags(Tags=[{'Key': TKey, 'Value': TValue}])

    # Only run 'WeeklySnapshot' on day 5 (Saturday)
    if now is not 5:
        tasks.remove('WeeklySnapshot')
    # Only run the 'MonthlySnapshot' on the last day of the month
    if DaysInMonth is not int(day):
        tasks.remove('MonthlySnapshot')
    # Run applicable tasks after filtering
    for task in tasks:
        period = ''
        TagType = task
        if TagType == 'DailySnapshot':
            period = 'day'
            DateSuffix = today.strftime('%a')
        elif TagType == 'WeeklySnapshot':
            period = 'week'
            DateSuffix = today.strftime('%U')
        elif TagType == 'MonthlySnapshot':
            period = 'month'
            DateSuffix = month
        log.info(f' [ Making {period} snapshots tagged: {TagType} ]')
        VolumeFilter = [{'Name': 'tag:' + TagType, 'Values': ['True']}]
        vols = ec2.volumes.filter(Filters=VolumeFilter)
        # Sping through volumes creating new snapshots / deleting old ones
        for vol in vols:
            VName = get_tag_name(vol.tags)
            log.info(f' - Taking snapshot of: {VName} ID: {vol.id}')
            try:
                CountTotal += 1
                TagsVolume = get_resource_tags(vol)

                description = f'{period}_snapshot {vol.id}'
                description += f'_{period}_{DateSuffix}'
                description += ' by Lambda snapshot script at '
                description += str(today.strftime('%d-%m-%Y %H:%M:%S'))
                try:
                    CurrentSnap = vol.create_snapshot(Description=description)
                    set_resource_tags(CurrentSnap, TagsVolume)

                    SuccessMsg = 'Snapshot created with description: '
                    SuccessMsg += f'{description} and tags: {TagsVolume}'

                    log.info(SuccessMsg)
                    TCreated += 1

                except Exception as e:
                    log.error(f'Unexpected error: {sys.exc_info()[0]}\n{e}')
                    pass

                log.info(f'- Deleting old snapshots for volume {vol.id}:')
                log.info(f'\tCurrent Snapshots for {vol.id}:')

                snapshots = vol.snapshots.all()
                DeleteList = []
                for snap in snapshots:
                    sdesc = str(snap.description)
                    if sdesc.startswith('week_snapshot') and period == 'week':
                        DeleteList.append(snap)
                    elif sdesc.startswith('day_snapshot') and period == 'day':
                        DeleteList.append(snap)
                    elif sdesc.startswith('month_snapshot') and period == 'month':
                        DeleteList.append(snap)
                    else:
                        log.info(f'Skipping {sdesc}, not added to delete list')
                for snap in DeleteList:
                    log.info(f'\t\t{snap.id} created: {snap.start_time}')

                def date_compare(snaps):
                    AllSnaps = {}
                    SortedSnaps = {}
                    SortedSnapsList = []
                    for item in snaps:
                        AllSnaps[int(item.start_time.timestamp())] = item
                    SortedSnaps = OrderedDict(sorted(AllSnaps.items()))
                    for key, value in SortedSnaps.items():
                        SortedSnapsList.append(value)

                    return SortedSnapsList

                DeleteList = date_compare(DeleteList)

                if period == 'day':
                    keep = KeepDay
                elif period == 'week':
                    keep = KeepWeek
                elif period == 'month':
                    keep = KeepMonth
                delta = len(DeleteList) - keep
                for i in range(delta):
                    log.info(f'Deleting snapshot: {DeleteList[i].description}')
                    DeleteList[i].delete()
                    TDeleted += 1
                time.sleep(3)
            except Exception as e:
                log.error(f'ERROR - {sys.exc_info()} on {vol.id} \n {e}')
                errmsg += f'Error in processing volume with id: {vol.id}'
                CountErr += 1
            else:
                CountSuccess += 1

    result = 'Finished making EBS snapshots at '
    result += str(datetime.today().strftime('%d-%m-%Y %H:%M:%S'))
    result += f' with {CountSuccess} snapshots of {CountTotal} possible.\n\n'

    message += result
    message += f'\nTotal snapshots created: {TCreated}'
    message += f'\nTotal snapshots errors: {CountErr}'
    message += f'\nTotal snapshots deleted: {TDeleted}\n'

    log.info(f'\n{message}\n')

    if errmsg:
        ErrSNSSubj = f'{AccountName} - Error with AWS Snapshots'
        ErrMsg = f'Error in processing volumes: {errmsg}'
        snsClient.publish(TopicArn=SNSARN, Message=ErrMsg, Subject=ErrSNSSubj)

    SNSSubj = f'{AccountName} - Finished AWS snapshotting'
    snsClient.publish(TopicArn=SNSARN, Message=message, Subject=SNSSubj)

    log.info(result)
