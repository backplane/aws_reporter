#!/usr/bin/env python3
""" utility which generates a CSV report from AWS API data on stdout """
import argparse
import csv
import json
import logging
import os
import shlex
import sys
from typing import Any, Dict, Final, List, Optional, Union

import boto3


class KeyPathNoDefault:
    """
    A token used by get_keypath to represent the absence of a default argument
    """

    pass


def get_keypath(
    obj: Dict,
    keypath_str: str,
    delimiter: str = ".",
    default: Any = KeyPathNoDefault,
) -> Any:
    """
    given a deeply nested object and a delimited keypath, retrieve the deep value at
    that keypath
    """
    keypath: List[str] = keypath_str.split(delimiter)
    sub_obj: Any = obj
    key: Union[str, int]
    for depth, key in enumerate(keypath):
        try:
            if isinstance(sub_obj, list):
                key = int(key)
            sub_obj = sub_obj[key]
        except KeyError:
            if default is not KeyPathNoDefault:
                return default
            raise KeyError(
                f"unable to resolve keypath '{keypath_str}'; failed to "
                f"retrieve '{key}' component (depth: {depth})"
            ) from None
    return sub_obj


def load_json_file(path: str, encoding: str = "utf-8") -> Any:
    """load the json file at the given path and return the parsed structure"""
    with open(path, "rt", encoding=encoding) as jsonfh:
        return json.load(jsonfh)


def cskv(data: Dict, kv_delimiter: str = "=", item_delimiter: str = ", ") -> str:
    """
    comma-separated key/value string: converts a dict into a comma-separated list of key
    and value pairs
    """
    # {'name': 'test', 'version': 2} -> "name=test, version=2"
    return item_delimiter.join(
        [f"{shlex.quote(k)}{kv_delimiter}{shlex.quote(v)}" for k, v in data.items()]
    )


def ec2_report(data: Any) -> int:
    """
    report on the ec2 instances
    """
    fields: Final = (
        "NameTag",
        "InstanceId",
        "InstanceType",
        "Placement.AvailabilityZone",
        "PlatformDetails",
        "PublicIpAddress",
        "LaunchTime",
        "State.Name",
        "StateTransitionReason",
        "Tags",
    )
    # this is a subset of the above, it identifies values that aren't directly
    # at a keypath
    computed_fields: Final = ("NameTag", "Tags")

    csvout = csv.DictWriter(sys.stdout, fields)
    csvout.writeheader()
    rowcount = 0

    for reservation in data["Reservations"]:
        for instance in reservation["Instances"]:
            outputs: Dict[str, str] = {
                key: get_keypath(instance, key, default="--")
                for key in fields
                if key not in computed_fields
            }
            tags = {kv["Key"]: kv["Value"] for kv in instance["Tags"]}
            # Promote the "Name" tag if there is one
            if "Name" in tags:
                outputs["NameTag"] = tags["Name"]
                del tags["Name"]
            outputs["Tags"] = cskv(tags)
            csvout.writerow(outputs)
            rowcount += 1

    logging.info("ec2_report: wrote %s rows", rowcount)
    return rowcount


def rds_report(data: Any) -> int:
    """
    report on the rds instances
    """
    fields: Final = (
        "DBInstanceIdentifier",
        "DBInstanceClass",
        "Engine",
        "DBInstanceStatus",
        "Endpoint.Address",
        "Endpoint.Port",
        "InstanceCreateTime",
        "AvailabilityZone",
        "MultiAZ",
        "StorageType",
        "DBInstanceArn",
        # "TagList",
    )
    # this is a subset of the above, it identifies values that aren't directly
    # at a keypath
    computed_fields: Final = ()

    csvout = csv.DictWriter(sys.stdout, fields)
    csvout.writeheader()
    rowcount = 0

    for instance in data["DBInstances"]:
        outputs: Dict[str, str] = {
            key: get_keypath(instance, key, default="--")
            for key in fields
            if key not in computed_fields
        }
        csvout.writerow(outputs)
        rowcount += 1

    logging.info("rds_report: wrote %s rows", rowcount)
    return rowcount


def sg_report(data: Any) -> int:
    fields: Final = (
        "GroupId",
        "SecurityGroupRuleId",
        "CidrIpv4",
        "Description",
        "ToPort",
    )
    # this is a subset of the above, it identifies values that aren't directly
    # at a keypath
    computed_fields: Final = ()

    csvout = csv.DictWriter(sys.stdout, fields)
    csvout.writeheader()
    rowcount = 0

    for rule in sorted(
        data["SecurityGroupRules"],
        key=lambda x: (x["GroupId"], x["SecurityGroupRuleId"]),
    ):
        # logging.debug("sg_report: rule %s", json.dumps(rule))
        outputs: Dict[str, str] = {
            key: get_keypath(rule, key, default="--")
            for key in fields
            if key not in computed_fields
        }
        csvout.writerow(outputs)
        rowcount += 1

    logging.info("sg_report: wrote %s rows", rowcount)
    return rowcount


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
        "--debug",
        action="store_true",
        help="enable debug output",
    )
    argp.add_argument(
        "--profile",
        type=str,
        default=default_profile,
        help="the AWS profile name to use for connecting to the API",
    )
    argp.add_argument(
        "--jsonfile",
        type=str,
        help=(
            "run the report against a JSON file instead of using the API - the file "
            "must be in the format returned by the commands: "
            "'aws rds describe-db-instances' or 'aws ec2 describe-instances'"
        ),
    )
    mode = argp.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ec2", action="store_true", help="run ec2 instance report")
    mode.add_argument("--rds", action="store_true", help="run rds instance report")
    mode.add_argument("--sg", action="store_true", help="run ec2 security group report")
    args = argp.parse_args()

    boto3.set_stream_logger("", logging.INFO)
    logging.basicConfig(
        stream=sys.stderr,
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    data = None
    if args.jsonfile:
        data = load_json_file(args.jsonfile)
    else:
        session = boto3.session.Session(profile_name=args.profile)
        if args.ec2:
            ec2 = session.client("ec2")
            data = ec2.describe_instances()
        elif args.rds:
            rds = session.client("rds")
            data = rds.describe_db_instances()
        elif args.sg:
            sg = session.client("ec2")
            data = sg.describe_security_group_rules()
        else:
            raise RuntimeError("unreachable code reached?")

    if args.ec2:
        ec2_report(data)
    elif args.rds:
        rds_report(data)
    elif args.sg:
        sg_report(data)
    else:
        raise RuntimeError("unreachable code reached?")

    return 0


if __name__ == "__main__":
    sys.exit(main())
