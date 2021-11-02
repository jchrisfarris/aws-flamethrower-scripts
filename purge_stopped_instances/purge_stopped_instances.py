#!/usr/bin/env python3
# Copyright 2021 Chris Farris <chrisf@primeharbor.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from botocore.exceptions import ClientError
from time import sleep
import boto3
import csv
import datetime as dt
import json
import logging
import os
import re
import sys


def main(args, logger):
    '''Executes the Primary Logic of the Fast Fix'''

    # If they specify a profile use it. Otherwise do the normal thing
    if args.profile:
        session = boto3.Session(profile_name=args.profile)
    else:
        session = boto3.Session()

    # Read the worklist from the passed in CSV file
    with open(args.infile, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for i in reader:
            logger.info(f"Processing {i['InstanceId']} ({i['tag.Name']}) in {i['Region']}")

            # Create a boto client in the correct region
            ec2_client = session.client("ec2", region_name=i['Region'])
            try:
                snapshot_ids = snapshot_instance(ec2_client, args, i)
                while not snapshots_creation_completed(ec2_client, snapshot_ids):
                    logger.debug(f"Snapshots not ready, sleeping 10 seconds")
                    sleep(10)
                terminate_stopped_instance(ec2_client, args, i)
            except ClientError as e:
                if e.response['Error']['Code'] == "InvalidInstanceID.NotFound" or e.response['Error']['Code'] == "InvalidParameterValue":
                    logger.warning(f"Unable to find Instance ID {i['InstanceId']} ({i['tag.Name']}) - No action taken")
                else:
                    raise


def snapshot_instance(ec2_client, args, i):
    '''Snapshot all the volumes attached to instance i'''
    output = []

    dry_run = not args.actually_do_it
    description = f"Created by {sys.argv[0]} from instance {i['InstanceId']} ({i['tag.Name']})"
    if args.snapshot_message:
        description += f" - {args.snapshot_message}"

    try:
        response = ec2_client.create_snapshots(
            Description=description,
            InstanceSpecification={
                'InstanceId': i['InstanceId'],
                'ExcludeBootVolume': False
            },
            DryRun=dry_run,
            CopyTagsFromSource='volume'
        )

        for s in response['Snapshots']:
            logger.info(f"Created Snapshot {s['SnapshotId']} for {s['VolumeId']} - Size {s['VolumeSize']}GB - State: {s['State']}")
            output.append(s['SnapshotId'])

        return(output)
    except ClientError as e:
        if e.response['Error']['Code'] == "DryRunOperation":
            logger.info(f"Would have created Snapshots for instance {i['InstanceId']} ({i['tag.Name']})")
            return(output)
        else:
            raise


def snapshots_creation_completed(client, snapshot_list):

    if snapshot_list == []:
        return(True)  # This is a dry-run

    response = client.describe_snapshots(SnapshotIds=snapshot_list)
    completed=True
    for s in response['Snapshots']:
        if s['State'] != "completed":
            completed=False
    return(completed)


def terminate_stopped_instance(ec2_client, args, i):

    if args.actually_do_it:
        logger.info(f"Terminating {i['InstanceId']} ({i['tag.Name']})")
        try:
            response = ec2_client.terminate_instances(InstanceIds=[i['InstanceId']])
        except ClientError as e:
            if e.response['Error']['Code'] == "OperationNotPermitted":
                if args.override_deletion_protection:
                    logger.info(f"Disabling Instance Termination protection on {i['InstanceId']} ({i['tag.Name']})")
                    ec2_client.modify_instance_attribute(InstanceId=i['InstanceId'], DisableApiTermination={'Value': False })
                    response = ec2_client.terminate_instances(InstanceIds=[i['InstanceId']])
                else:
                    logger.warning(f"Instance {i['InstanceId']} ({i['tag.Name']}) has instance protection. Unable to proceed")
            elif e.response['Error']['Code'] == "InvalidInstanceID.NotFound":
                logger.warning(f"Unable to find Instance ID {i['InstanceId']} ({i['tag.Name']}) - No action taken")
            else:
                raise
    else:
        logger.info(f"Would Terminate {i['InstanceId']} ({i['tag.Name']})")


def do_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="print debugging info", action='store_true')
    parser.add_argument("--error", help="print error info only", action='store_true')
    parser.add_argument("--timestamp", help="Output log with timestamp and toolname", action='store_true')
    parser.add_argument("--profile", help="Use this CLI profile (instead of default or env credentials)")
    parser.add_argument("--actually-do-it", help="Actually Perform the snapshot and deletion", action='store_true')
    parser.add_argument("--snapshot-message", help="Append this to the description of the Snapshot.")
    parser.add_argument("--infile", help="CSV File of instances to Snapshot and Terminate", required=True)
    parser.add_argument("--override-deletion-protection", help="Modify the instance's disableApiTermination attribute if necessary to terminate the instance", action='store_true')

    args = parser.parse_args()

    return(args)

if __name__ == '__main__':

    args = do_args()

    # Logging idea stolen from: https://docs.python.org/3/howto/logging.html#configuring-logging
    # create console handler and set level to debug
    logger = logging.getLogger(sys.argv[0])
    ch = logging.StreamHandler()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    elif args.error:
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.INFO)

    # Silence Boto3 & Friends
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # create formatter
    if args.timestamp:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        formatter = logging.Formatter('%(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    try:
        main(args, logger)
    except KeyboardInterrupt:
        exit(1)