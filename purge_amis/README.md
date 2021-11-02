# Purge AMIs

These two scripts will allow you purge all the AMIs and associated snapshots older than X date in your account.


## What these scripts do

The first script `list_amis_to_delete.py` will create a CVS file of all the snapshots created more than a certian number of days ago. You can review this CSV file in Excel prior to taking any action in the account.

The second script `purge_amis.py` will take the (possibly modified) CSV file from `list_amis_to_delete.py` and delete the snapshot.

You can specify how old a snapshot is before it is to be purged by passing `--older-than-days` to the
The first script `list_amis_to_delete.py` script.

WARNING: This script will delete any Snapshots that were in use by a deleted AMI.

## Usage

**Usage for list_amis_to_delete.py**
```
usage: list_amis_to_delete.py [-h] [--debug] [--error] [--timestamp]
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
                        Only return AMIs older than X days
```

**Usage for purge_amis.py**
```
usage: purge_amis.py [-h] [--debug] [--error] [--timestamp]
                     [--profile PROFILE] [--actually-do-it] --infile INFILE

optional arguments:
  -h, --help         show this help message and exit
  --debug            print debugging info
  --error            print error info only
  --timestamp        Output log with timestamp and toolname
  --profile PROFILE  Use this CLI profile (instead of default or env
                     credentials)
  --actually-do-it   Actually Perform the snapshot and deletion
  --infile INFILE    CSV File of images to deregister and delete associated snapshots
```

You must specify `--actually-do-it` for the changes to be made. Otherwise the script runs in dry-run mode only.


