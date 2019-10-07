#!/usr/bin/env python3
import json
import boto3
import logging
import time
import datetime


# Output logging - Set to INFO for full output in cloudwatch
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Define boto3 connections/variables
ec2 = boto3.resource('ec2')
# Getting the Account ID needed to filter snapshots/AMIs
MyAWSID = boto3.client('sts').get_caller_identity().get('Account')

# Label applied to anything not named and un-attached
UnattachedLabel = '- UNATTACHED - '
# Used as a temp variable to identify things without names
no_name_label = "(no name)"
# This is the prefix that automatically comes on marketplace ami-snapshots
generic_snapshot = "Created by CreateImage"


# Finds the AWS Tag:Name.value in a dict of tags
def get_tag_name(all_tags):
    if all_tags is not None:
        for tags in all_tags:
            if tags["Key"] == 'Name':
                name_tag = tags["Value"]
    else:
        name_tag = no_name_label
    return name_tag


# get all the instances and their name tags to avoid multiple lookups
class instance_ids:

    def __init__(self):
        self.names = {}
        instances = list(ec2.instances.all())
        for inst in instances:
            self.names[inst.id] = get_tag_name(ec2.Instance(inst.id).tags)

    def name(self, id):
        if id in self.names:
            return(self.names[id])
        else:
            return(False)


# Iteration counter for naming passes / debugging
class counter:
        def __init__(self):
                self.number = 0
                self.total = 0

        def add(self):
                self.number += 1
                self.total += 1

        def reset(self):
                self.number = 0


# AMI rename process
def rename_amis(counter):
    log.info('[ OWNED AMI LABELING TASK STARTING ]')
    AMIFilter = {'Name': 'owner-id', 'Values': [MyAWSID]}
    AllAMIs = ec2.images.filter(Filters=[AMIFilter])
    for image in AllAMIs:
        AMIName = image.name
        dob = image.creation_date[0:10]
        ImgName = get_tag_name(image.tags)
        if ImgName.startswith(no_name_label) or len(ImgName) == 0:
            AMIName += " " + dob
            log.info(f'Labeling Image: {image.id} with {AMIName}')
            ImgNewName = [{'Key': 'Name', 'Value': AMIName}]
            image.create_tags(Tags=ImgNewName)
            counter.add()
        else:
            log.info(f'\t - AMI {image.id} already has a name: {ImgName}')
    log.info(f'[ AMI TASK FINISHED, {counter.number} AMIS LABELED ]')
    counter.reset()


# EBS rename process
def rename_ebs_volumes(EC2IDs, counter):
    log.info('[ VOLUME RENAME TASK STARTING ]')
    for volume in ec2.volumes.all():
        VolumeName = get_tag_name(volume.tags)
        if 'in-use' in volume.state:
            InstanceID = volume.attachments[0]['InstanceId']
            InstMount = volume.attachments[0]['Device']
            InstName = EC2IDs.name(InstanceID)
            NewVolName = f'[ {InstName} ]-{InstMount}'
            VolTagNewName = [{'Key': 'Name', 'Value': NewVolName}]
            if VolumeName is not NewVolName:
                volume.create_tags(Tags=VolTagNewName)
                log.info(f'\t - EBS: {volume.id} renamed {NewVolName}')
                counter.add()
            else:
                log.info(f'\t - EBS {volume.id} named correctly: {NewVolName}')
        if volume.state is 'available':
            NewVolName = UnattachedLabel + VolumeName
            VolTagNewName = [{'Key': 'Name', 'Value': NewVolName}]
            if not VolumeName.startswith(UnattachedLabel):
                volume.create_tags(Tags=VolTagNewName)
                log.info(f'\t - EBS {volume.id} renamed: {NewVolName}')
                counter.add()
            else:
                log.info(f'\t - EBS {volume.id} correctly named: {NewVolName}')
    log.info(f'[ VOLUME TASK FINISHED, {counter.number} VOLUMES RENAMED ]')
    counter.reset()


# Network Interface rename process
def rename_interfaces(EC2IDs, counter):
    log.info('[ INTERFACE RENAME TASK STARTING ]')
    for interface in ec2.network_interfaces.all():
        NICNewName = '[ no attachment status ]'
        if 'in-use' in interface.status:
            if 'InstanceId' in interface.attachment:
                EC2ID = interface.attachment['InstanceId']
                if EC2ID is not None:
                    NICNewName = EC2IDs.name(EC2ID)
                else:
                    NICNewName = 'No-Instance-ID'
            else:
                try:
                    NICNewName = Interface['Description']
                except Exception as e:
                    NICNewName = 'non-ec2-nic'
                    log.info(f'Interface isn\'t an EC2 instance: {e}')
        if interface.status is 'available':
            NICNewName = UnattachedLabel
        InterfacesNewName = [{'Key': 'Name', 'Value': NICNewName}]
        interface.create_tags(Tags=InterfacesNewName)
        log.info(f'\t - Interface {interface.id} renamed {NICNewName}')
        counter.add()
    log.info(f'[ INTERFACE TASK FINISHED, {counter.number} NICS RENAMED ]')
    counter.reset()


# Snapshot rename process
def rename_snapshots(counter):
    log.info('[ SNAPSHOT LABELING TASK STARTING ]')
    SnapShotFilter = {'Name': 'owner-id', 'Values': [MyAWSID]}
    AllSnapShots = ec2.snapshots.filter(Filters=[SnapShotFilter])
    for snapshot in AllSnapShots:
        ssid = snapshot.id
        desc = snapshot.description
        dob = snapshot.start_time.strftime("%m/%d/%y")
        SnapName = get_tag_name(snapshot.tags)
        if SnapName.startswith(no_name_label) or len(SnapName) == 0:
            NewSnapName = None
            if snapshot.description.startswith(generic_snapshot):
                if snapshot.volume_id is not None:
                    ssvid = snapshot.volume_id
                    try:
                        VolumeTags = ec2.Volume(ssvid).tags
                        NewSnapName = get_tag_name(VolumeTags)
                    except Exception:
                        log.info(f'\t- NO CURRENT VOLUME WITH ID : {ssvid}')
                        NewSnapName = f'Old-{ssvid}-Snapshot-{dob}'
                else:
                    NewSnapName = f'CreateImage {ssvid}-Snapshot-{dob}'
            else:
                NewSnapName = desc
            if NewSnapName:
                log.info(f'\t- Labeling Snapashot {ssid} as {NewSnapName}')
                SnapNewNameTag = [{'Key': 'Name', 'Value': NewSnapName}]
                snapshot.create_tags(Tags=SnapNewNameTag)
                counter.add()
            else:
                log.error(f'\t- COULD NOT DETERMINE A NAME FOR: {ssid}')
        else:
            log.info(f'\t - Snapshot: {ssid} already tagged as {SnapName}')
    log.info(f'[ SNAPSHOT TASK FINISHED, {counter.number} SNAPS LABELED ]')
    counter.reset()


# Main function
def lambda_handler(event, context):
    EC2Instances = instance_ids()
    RenameCounter = counter()
    log.info('[ - RENAME PROGRAM STARTING - ]')
    rename_ebs_volumes(EC2Instances, RenameCounter)
    rename_interfaces(EC2Instances, RenameCounter)
    rename_snapshots(RenameCounter)
    rename_amis(RenameCounter)
    log.info(f'[ - RENAME FINSIHED, {RenameCounter.total} OBJECTS RENAMED - ]')
