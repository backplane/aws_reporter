#!/usr/bin/env python3
""" utility which generates a CSV report from AWS API data on stdout """
import argparse
import logging
import os
import sys
from typing import Optional

import boto3

from .aws import EC2, RDS, SG, Reporter


def main() -> int:
    """
    entrypoint for direct execution; returns an integer suitable for use with sys.exit
    """

    default_profile: Optional[str] = "default"
    if os.environ.get("AWS_EXECUTION_ENV") == "CloudShell":
        default_profile = None

    argp = argparse.ArgumentParser(
        prog=__package__,
        description=("generates a CSV report from AWS API data on stdout"),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    argp.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="enable debug output",
    )
    argp.add_argument(
        "-p",
        "--profile",
        type=str,
        default=default_profile,
        help="the AWS profile name to use for connecting to the API",
    )
    argp.add_argument(
        "-i",
        "--inputjson",
        type=str,
        help=(
            "run the report against a JSON file instead of using the API - the file "
            "must be in the format returned by the commands: "
            "'aws rds describe-db-instances' or 'aws ec2 describe-instances'"
        ),
    )
    argp.add_argument(
        "mode",
        choices=(EC2, RDS, SG),
        help="select a report to run",
    )
    args = argp.parse_args()

    boto3.set_stream_logger("", logging.INFO)
    logging.basicConfig(
        stream=sys.stderr,
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    reporter = Reporter(args.profile, args.inputjson)
    {
        EC2: reporter.ec2_report,
        RDS: reporter.rds_report,
        SG: reporter.sg_report,
    }[args.mode]()

    return 0


if __name__ == "__main__":
    sys.exit(main())
