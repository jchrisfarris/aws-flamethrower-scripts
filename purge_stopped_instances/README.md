# Purge Stopped Instances

These two scripts will allow you to snapshot and terminate _all_ stopped instances in your account.


## What these scripts do

The first script `list_instances_to_terminate.py` will create a CVS file of all the stopped instances in the account that have been stopped more than a certian number of days. You can review this CSV file in Excel prior to taking any action in the account.

The second script `purge_stopped_instances.py` will take the (possibly modified) CSV file from `list_instances_to_terminate.py`. For each instance in the CSV it will first take a snapshot of the volumes attached to the instance and then it will terminate the instance.

You can specify how long an instance has been stopped before it is to be purged by passing `--older-than-days` to the
The first script `list_instances_to_terminate.py` script.

If EC2 Termination Protection is enabled, you can specify `--override-deletion-protection` to first remove the disableApiTermination attribute.


## Usage

**Usage for list_instances_to_terminate.py**
```
usage: list_instances_to_terminate.py [-h] [--debug] [--error] [--timestamp]
                                      [--region REGION] [--profile PROFILE]
                                      [--outfile OUTFILE]
                                      [--older-than-days OLDER_THAN_DAYS]

optional arguments:
  -h, --help            show this help message and exit
  --debug               print debugging info
  --error               print error info only
  --timestamp           Output log with timestamp and toolname
  --region REGION       Only Process Specified Region
  --profile PROFILE     Use this CLI profile (instead of default or env credentials)
  --outfile OUTFILE     Save the list of Instances to this file
  --older-than-days OLDER_THAN_DAYS
                        Only Snapshot and Terminate Instances that have been stopped more than X days
```

**Usage for purge_stopped_instances.py**
```
usage: purge_stopped_instances.py [-h] [--debug] [--error] [--timestamp]
                                  [--region REGION] [--profile PROFILE]
                                  [--actually-do-it]
                                  [--snapshot-message SNAPSHOT_MESSAGE]
                                  --infile INFILE
                                  [--override-deletion-protection]

optional arguments:
  -h, --help            show this help message and exit
  --debug               print debugging info
  --error               print error info only
  --timestamp           Output log with timestamp and toolname
  --region REGION       Only Process Specified Region
  --profile PROFILE     Use this CLI profile (instead of default or env credentials)
  --actually-do-it      Actually Perform the snapshot and deletion
  --snapshot-message SNAPSHOT_MESSAGE
                        Append this to the description of the Snapshot.
  --infile INFILE       CSV File of instances to Snapshot and Terminate
  --override-deletion-protection
                        Modify the instance's disableApiTermination attribute if necessary to terminate the instance
```

You must specify `--actually-do-it` for the changes to be made. Otherwise the script runs in dry-run mode only.


