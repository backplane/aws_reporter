#!/usr/bin/env python3
""" misc utility functions """
import datetime
import hashlib
import json
import pickle  # nosec: ephemeral use for hash computation
import shlex
from typing import Any, Dict, List, Union


def hash_args_kwargs(*args, **kwargs) -> str:
    """return the hash of the given args/kwargs"""
    pickled_args = pickle.dumps(args)
    pickled_kwargs = pickle.dumps(kwargs)
    return hashlib.sha256(pickled_args + pickled_kwargs).hexdigest()


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


def utcnow() -> datetime.datetime:
    """reimplementation of deprecated datetime.datetime.utcnow"""
    return datetime.datetime.now(datetime.UTC)


class KeyPathNoDefault(Exception):
    """
    A token used by get_keypath to represent the absence of a default argument
    """


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
