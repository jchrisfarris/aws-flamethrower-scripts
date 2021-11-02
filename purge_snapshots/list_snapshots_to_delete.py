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

import pytz
utc=pytz.UTC

EBS_HEADER=["SnapshotId", "Type", "Region", "StartTime", "VolumeSize", "State", "Description"]
RDS_HEADER=["DBSnapshotIdentifier", "Type", "Region", "SnapshotCreateTime", "AllocatedStorage", "Status", "DBInstanceIdentifier"]


def main(args, logger):
    '''Executes the Primary Logic of the Fast Fix'''

    # If they specify a profile use it. Otherwise do the normal thing
    if args.profile:
        session = boto3.Session(profile_name=args.profile)
    else:
        session = boto3.Session()

    snapshots = []  # array of rows to pass to DictWriter
    tag_keys = ["tag.Name"]  # We need to pass all the tag keys to the DictWriter

    # Get all the Regions for this account
    for region in get_regions(session, args):
        if args.type == "EBS":
            snap_list = list_snapshots(session, region, args)
            logger.info(f"Found {len(snap_list)} snapshots to cleanup in {region}")
            csv_header = EBS_HEADER
            for s in snap_list:
                s['Region'] = region
                s['Type'] = "EBS"
                # parse the annoying way AWS returns tags into a proper dict
                if 'Tags' in s:
                    tags = parse_tags(s['Tags'])
                    for key, value in tags.items():
                        # we need to capture the list of tag_keys for Dictwriter, but we prepend with "tag." to avoid
                        # overriding an instance key
                        if f"tag.{key}" not in tag_keys:
                            tag_keys.append(f"tag.{key}")
                        s[f"tag.{key}"] = value  # now add to the instance dict
                snapshots.append(s)
        elif args.type == "RDS":
            snap_list = list_rds_snapshots(session, region, args)
            logger.info(f"Found {len(snap_list)} snapshots to cleanup in {region}")
            csv_header = RDS_HEADER
            for s in snap_list:
                s['Region'] = region
                s['Type'] = "RDS"
                # parse the annoying way AWS returns tags into a proper dict
                tags = parse_tags(s['TagList'])
                for key, value in tags.items():
                    # we need to capture the list of tag_keys for Dictwriter, but we prepend with "tag." to avoid
                    # overriding an instance key
                    if f"tag.{key}" not in tag_keys:
                        tag_keys.append(f"tag.{key}")
                    s[f"tag.{key}"] = value  # now add to the instance dict
                snapshots.append(s)
        else:
            logger.critical(f"Invalid type: {args.type}. Aborting...")
            exit(1)

    # Now write the final CSV file
    with open(args.outfile, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_header + tag_keys, extrasaction='ignore')
        writer.writeheader()
        for s in snapshots:
            writer.writerow(s)
    exit(0)

def list_snapshots(session, region, args):
    ec2_client = session.client("ec2", region_name=region)
    output = []
    response = ec2_client.describe_snapshots(
        OwnerIds=['self'],
        MaxResults=1000
    )
    threshold_time = utc.localize(dt.datetime.today() - dt.timedelta(days=int(args.older_than_days)))
    logger.info(f"Looking for Snapshots older than {threshold_time}")
    for s in response['Snapshots']:
        if s['StartTime'] < threshold_time:
            logger.debug(f"Snapshot {s['SnapshotId']} was created {s['StartTime']}, which is older that {threshold_time}")
            output.append(s)

    return(output)

def list_rds_snapshots(session, region, args):
    client = session.client("rds", region_name=region)
    output = []
    response = client.describe_db_snapshots(
        MaxRecords=100,
        SnapshotType='manual'
    )
    threshold_time = utc.localize(dt.datetime.today() - dt.timedelta(days=int(args.older_than_days)))
    logger.info(f"Looking for Snapshots older than {threshold_time}")
    for s in response['DBSnapshots']:
        if s['SnapshotCreateTime'] < threshold_time:
            logger.debug(f"Snapshot {s['DBSnapshotIdentifier']} was created {s['SnapshotCreateTime']}, which is older that {threshold_time}")
            output.append(s)

    return(output)


def parse_tags(tagset):
    output = {}
    for t in tagset:
        output[t['Key']] = t['Value']
    return(output)


def get_regions(session, args):
    '''Return a list of regions with us-east-1 first. If --region was specified, return a list wth just that'''

    # If we specifed a region on the CLI, return a list of just that
    if args.region:
        return([args.region])

    # otherwise return all the regions, us-east-1 first
    ec2 = session.client('ec2', region_name="us-east-1")
    response = ec2.describe_regions()
    output = ['us-east-1']
    for r in response['Regions']:
        # return us-east-1 first, but dont return it twice
        if r['RegionName'] == "us-east-1":
            continue
        output.append(r['RegionName'])
    return(output)


def do_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="print debugging info", action='store_true')
    parser.add_argument("--error", help="print error info only", action='store_true')
    parser.add_argument("--timestamp", help="Output log with timestamp and toolname", action='store_true')
    parser.add_argument("--region", help="Only Process Specified Region")
    parser.add_argument("--profile", help="Use this CLI profile (instead of default or env credentials)")
    parser.add_argument("--outfile", help="Save the list of Instances to this file", default="snapshots-to-delete.csv")
    parser.add_argument("--older-than-days", help="Only return snapshots older than X days", default=365)
    parser.add_argument("--type", help="Purge EBS or RDS Snapshots", choices=["EBS", "RDS"], default="EBS")

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
    except ClientError as e:
        if e.response['Error']['Code'] == "RequestExpired":
            print("Credentials expired")
            exit(1)
        else:
            raise