""" 
Purpose: Provides utility functions.
Functionality: Contains helper functions for time conversion, file manipulation, and environment variable management.
Connection: Utility functions are used across different modules for common tasks.

 """

import os
import re
from typing import Callable
from datetime import datetime
from datetime import timezone

import functools
import itertools
import yaml

from backend.internal.errors import OxnException

SECONDS_MAP = {
    "us": 1 / 10 ** 6,
    "ms": 1 / 10 ** 3,
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
}
"""Map used to convert time strings to seconds"""

time_string_format_regex = r"(\d+)(us|ms|s|m|h|d)"


def validate_time_string(time_string):
    """
    Validate that a time string has units

    """
    return bool(re.match(time_string_format_regex, time_string))


def time_string_to_seconds(time_string) -> float:
    """Convert a time string with units to a float"""
    matches = re.findall(time_string_format_regex, time_string)
    seconds = 0.0
    for match in matches:
        value_part = match[0]
        unit_part = match[1]
        seconds += float(value_part) * SECONDS_MAP[unit_part]
    return seconds


def to_milliseconds(seconds):
    """Convert seconds to milliseconds"""
    return seconds * 10 ** 3


def to_microseconds(seconds):
    """Convert seconds to microseconds"""
    return seconds * 10 ** 6


def utc_timestamp() -> float:
    """Get the current time in """
    return datetime.now(timezone.utc).timestamp()


def humanize_utc_timestamp(timestamp):
    """Return a human-readable version of a timestamp"""
    return datetime.utcfromtimestamp(timestamp)


def add_env_variable(compose_file_path, service_name, variable_name, variable_value):
    """Add an environment variable with a given value to a service in a Docker Compose file"""
    with open(compose_file_path, "r") as file:
        compose_dict = yaml.safe_load(file)

    if service_name not in compose_dict["services"]:
        raise OxnException(explanation=f"Service {service_name} not found in Docker Compose file")

    if "environment" not in compose_dict["services"][service_name]:
        compose_dict["services"][service_name]["environment"] = []

    environment = compose_dict["services"][service_name]["environment"]
    exists = False
    if isinstance(environment, list):
        for idx, env_var in enumerate(environment):
            if env_var.startswith(f"{variable_name}="):
                environment[idx] = f"{variable_name}={variable_value}"
                exists = True
        if not exists:
            environment.append(f"{variable_name}={variable_value}")
    else:
        raise OxnException(explanation="Environment field for %s is not a list" % service_name)

    with open(compose_file_path, "w") as file:
        yaml.safe_dump(compose_dict, file)


def remove_env_variable(compose_file_path, service_name, variable_name, variable_value):
    """Remove an environment variable from a service in a Docker Compose file"""
    with open(compose_file_path, "r") as file:
        compose_dict = yaml.safe_load(file)

    if service_name not in compose_dict["services"]:
        raise OxnException(explanation=f"Service {service_name} not found in Docker Compose file")

    if "environment" in compose_dict["services"][service_name]:
        idx = compose_dict["services"][service_name]["environment"].index(f"{variable_name}={variable_value}")
        compose_dict["services"][service_name]["environment"].remove(idx)

    with open(compose_file_path, "w") as file:
        yaml.safe_dump(compose_dict, file)

def dict_product(options):
    """Generate all possible combinations of parameter variations
    
    Args:
        options: Dictionary with parameter paths as keys and lists of values
        
    Returns:
        List of dictionaries containing all possible combinations of parameters
        
    Example:
        Input: {
            "experiment.treatments.1.params.duration": ["99m", "120m"],
            "experiment.treatments.1.params.delay": ["99m", "120m"]
        }
        Output: [
            {
                "experiment.treatments.1.params.duration": "99m",
                "experiment.treatments.1.params.delay": "99m"
            },
            {
                "experiment.treatments.1.params.duration": "99m", 
                "experiment.treatments.1.params.delay": "120m"
            },
            ...
        ]
    """
    keys = options.keys()
    values = options.values()
    combinations = []
    
    for combination in itertools.product(*values):
        combinations.append(dict(zip(keys, combination)))
        
    return combinations

def update_dict_with_parameter_variations(config: dict, parameter_variations: dict) -> dict:
    """
    Updates a nested dictionary (returns a copy) with parameter variations specified in dot notation.
    
    Args:
        config: The original configuration dictionary to update
        parameter_variations: Dictionary with keys in dot notation and values to update
        
    Example parameter_variations:
    {
        "experiment.treatments.0.params.duration": "1m",
        "experiment.treatments.0.params.delay": 10
    }
    
    Returns:
        Updated configuration dictionary
        
    Raises:
        KeyError: If a key in the path does not exist in the original config
        IndexError: If an array index is out of bounds
    """
    config = config.copy()
    
    for param_path, value in parameter_variations.items():
        # Split the path into parts
        path_parts = param_path.split('.')
        
        # Start at the root of the config
        current = config
        
        # Traverse to the second-to-last part to get the parent
        for part in path_parts[:-1]:
            # Handle array indices
            if part.isdigit():
                part = int(part)
                if not isinstance(current, list):
                    raise KeyError(f"Expected list but found {type(current)} at path {param_path}")
                if part >= len(current):
                    raise IndexError(f"Index {part} is out of bounds for list of length {len(current)} at path {param_path}")
            
            # Check if key exists in dict
            elif isinstance(part, str):
                if part not in current:
                    raise KeyError(f"Key '{part}' not found in config at path {param_path}")
                
            current = current[part]
            
        # Set the final value
        if path_parts[-1] not in current and not isinstance(current, list):
            raise KeyError(f"Final key '{path_parts[-1]}' not found in config at path {param_path}")
            
        current[path_parts[-1]] = value
        
    return config