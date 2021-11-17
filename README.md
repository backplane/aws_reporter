# aws_reporter

A utility script for generating CSV reports from data pulled from the AWS API.

## Usage

The program prints its output to the standard output. Use the profile name to select the correct API credentials.

This is help text printed when the program is invoked with `-h` or `--help` arguments:

```
usage: reporter.py [-h] [--debug] [--profile PROFILE] [--jsonfile JSONFILE] (--ec2 | --rds)

generates a CSV report from AWS API data on stdout

optional arguments:
  -h, --help           show this help message and exit
  --debug              enable debug output (default: False)
  --profile PROFILE    the AWS profile name to use for connecting to the API (default: default)
  --jsonfile JSONFILE  run the report against a JSON file instead of using the API - the file must be in the format returned by the commands: 'aws rds describe-db-instances' or 'aws ec2 describe-instances'
                       (default: None)
  --ec2                run the EC2 instance report (default: False)
  --rds                run the RDS instance report (default: False)

```

### Example Invocation

In the following example, output is being directed to the file `ec2.csv` and the profile named "project3" is being used.

```sh
$ ./reporter.py --profile project3 --ec2 >ec2.csv
2021-11-17 19:20:05,494 botocore.credentials [INFO] Found credentials in shared credentials file: ~/.aws/credentials
2021-11-17 19:20:06,334 root [INFO] ec2_report: wrote 14 rows
```