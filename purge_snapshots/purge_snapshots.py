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
    # If they specify a profile use it. Otherwise do the normal thing
    if args.profile:
        session = boto3.Session(profile_name=args.profile)
    else:
        session = boto3.Session()

    size_deleted = 0

    # Read the worklist from the passed in CSV file
    with open(args.infile, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for s in reader:
            # Create a boto client in the correct region
            ec2_client = session.client("ec2", region_name=s['Region'])
            try:
                if args.actually_do_it:
                    ec2_client.delete_snapshot(SnapshotId=s['SnapshotId'])
                    logger.info(f"Deleted {s['SnapshotId']} ({s['Description']}) in {s['Region']}")
                else:
                    logger.info(f"Would Delete {s['SnapshotId']} ({s['Description']}) in {s['Region']}")
                size_deleted += int(s['VolumeSize'])
            except ClientError as e:
                if e.response['Error']['Code'] == "InvalidSnapshot.InUse":
                    logger.error(f"Unable to delete {s['SnapshotId']} - {e}")
                elif e.response['Error']['Code'] == "InvalidSnapshot.NotFound":
                    logger.error(f"Unable to find {s['SnapshotId']}")
                else:
                    raise

    if args.actually_do_it:
        logger.info(f"Deleted {size_deleted}GB of Snapshots")
    else:
        logger.info(f"Would delete {size_deleted}GB of Snapshots")

def do_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", help="print debugging info", action='store_true')
    parser.add_argument("--error", help="print error info only", action='store_true')
    parser.add_argument("--timestamp", help="Output log with timestamp and toolname", action='store_true')
    parser.add_argument("--profile", help="Use this CLI profile (instead of default or env credentials)")
    parser.add_argument("--actually-do-it", help="Actually Perform the snapshot and deletion", action='store_true')
    parser.add_argument("--infile", help="CSV File of Snapshots to delete", required=True)

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