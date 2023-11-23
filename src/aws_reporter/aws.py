#!/usr/bin/env python3
""" class for reporting on aws instances """
import csv
import datetime
import logging
import sys
from collections import defaultdict
from typing import Any, Dict, Final, Optional, Union

import boto3

from .utils import cskv, get_keypath, hash_args_kwargs, load_json_file, utcnow

# aws-related constants

# services
EC2: Final = "ec2"
RDS: Final = "rds"
SG: Final = "sg"
CLOUDWATCH: Final = "cloudwatch"

# methods
DESCRIBE_DB_INSTANCES: Final = "describe_db_instances"
DESCRIBE_INSTANCES: Final = "describe_instances"
DESCRIBE_SECURITY_GROUP_RULES: Final = "describe_security_group_rules"
GET_METRIC_STATISTICS: Final = "get_metric_statistics"


logger = logging.getLogger(__name__)


class Reporter:
    """class for reporting on AWS resources"""

    session: boto3.Session
    cache: Dict[str, Dict[str, Dict[str, Any]]]

    def __init__(self, profile_name: str, input_json: Optional[str] = None) -> None:
        self.session = boto3.session.Session(profile_name=profile_name)
        self.cache = defaultdict(lambda: defaultdict(dict))
        if input_json:
            data = load_json_file(input_json)
            for client_name in data:
                for method_name in client_name:
                    self.cache[client_name][method_name] = data[client_name][
                        method_name
                    ]

    def get_data(
        self,
        client: str,
        method: str,
        *args,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """make an API call utilizing the cache"""

        cache_key = hash_args_kwargs(*args, **kwargs)

        if data := self.cache[client][method].get(cache_key):
            return data
        data = getattr(self.session.client(client), method)(*args, **kwargs)
        if data:
            self.cache[client][method][cache_key] = data
        return data

    def ec2_report(self) -> int:
        """
        report on the ec2 instances
        """
        data = self.get_data(EC2, DESCRIBE_INSTANCES)
        if data is None:
            raise ValueError("no result returned from get_data")

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

        logger.info("ec2_report: wrote %s rows", rowcount)
        return rowcount

    def get_rds_free_storage(self, db_instance_id: str) -> int:
        """return the amount of space available on the given RDS instance (in bytes)"""
        data = self.get_data(
            CLOUDWATCH,
            GET_METRIC_STATISTICS,
            Namespace="AWS/RDS",
            MetricName="FreeStorageSpace",
            Dimensions=[
                {
                    "Name": "DBInstanceIdentifier",
                    "Value": db_instance_id,
                },
            ],
            StartTime=utcnow() - datetime.timedelta(hours=1),
            EndTime=utcnow(),
            Period=3600,
            Statistics=["Average"],
        )
        if data is None:
            raise ValueError("no result returned from get_data")

        # Print the free storage space
        if data["Datapoints"]:
            return data["Datapoints"][0]["Average"]

        return -1

    def rds_report(self) -> int:
        """
        report on the rds instances
        """
        data = self.get_data(RDS, DESCRIBE_DB_INSTANCES)
        if data is None:
            raise ValueError("no result returned from get_data")

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
            "AllocatedStorage",
            # "TagList",
        )
        # this is a subset of the above, it identifies values that aren't directly
        # at a keypath
        computed_fields: Final = ()

        csvout = csv.DictWriter(
            sys.stdout,
            fields
            + (
                "AllocatedStorageGiB",
                "UsedStorageGiB",
                "FreeStorageGiB",
                "StorageUtilizationPercentage",
            ),
        )
        csvout.writeheader()
        rowcount = 0

        for instance in data["DBInstances"]:
            outputs: Dict[str, Union[str, int, float]] = {
                key: get_keypath(instance, key, default="--")
                for key in fields
                if key not in computed_fields
            }
            allocated_bytes: int = int(outputs["AllocatedStorage"]) * 1073742000
            free_bytes: int = self.get_rds_free_storage(
                instance["DBInstanceIdentifier"]
            )
            free_gib = free_bytes * 9.313226e-10
            if free_bytes < 1:
                free_gib = -1
            storage_used = allocated_bytes - free_bytes

            outputs["AllocatedStorageGiB"] = outputs["AllocatedStorage"]  # an alias
            outputs["UsedStorageGiB"] = storage_used * 9.313226e-10
            outputs["FreeStorageGiB"] = free_gib
            outputs["StorageUtilizationPercentage"] = round(
                (storage_used / allocated_bytes) * 100, 2
            )

            csvout.writerow(outputs)
            rowcount += 1

        logger.info("rds_report: wrote %s rows", rowcount)
        return rowcount

    def sg_report(self) -> int:
        """
        report on security groups
        """
        data = self.get_data(EC2, DESCRIBE_SECURITY_GROUP_RULES)
        if data is None:
            raise ValueError("no result returned from get_data")

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
            # logger.debug("sg_report: rule %s", json.dumps(rule))
            outputs: Dict[str, str] = {
                key: get_keypath(rule, key, default="--")
                for key in fields
                if key not in computed_fields
            }
            csvout.writerow(outputs)
            rowcount += 1

        logger.info("sg_report: wrote %s rows", rowcount)
        return rowcount
