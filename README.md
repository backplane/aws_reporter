# aws_reporter

A utility script for generating CSV reports from data pulled from the AWS API.

## Usage

The program prints its output to the standard output. Use the profile name to select the correct API credentials.

This is help text printed when the program is invoked with `-h` or `--help` arguments:

```
usage: aws_reporter [-h] [-d] [-p PROFILE] [-i INPUTJSON] {ec2,rds,sg}

generates a CSV report from AWS API data on stdout

positional arguments:
  {ec2,rds,sg}          select a report to run

options:
  -h, --help            show this help message and exit
  -d, --debug           enable debug output (default: False)
  -p PROFILE, --profile PROFILE
                        the AWS profile name to use for connecting to the API (default: default)
  -i INPUTJSON, --inputjson INPUTJSON
                        run the report against a JSON file instead of using the API - the file must be in the format returned by the commands: 'aws rds describe-db-instances' or 'aws ec2 describe-instances'
                        (default: None)
```

### Example Invocation

In the following example, output is being directed to the file `ec2.csv` and the profile named "project3" is being used.

```sh
$ docker run --rm --volume ~/.aws:/work/.aws backplane/aws_reporter --profile project3 ec2 >ec2.csv
2021-11-17 19:20:05,494 botocore.credentials [INFO] Found credentials in shared credentials file: ~/.aws/credentials
2021-11-17 19:20:06,334 root [INFO] ec2_report: wrote 14 rows
```
