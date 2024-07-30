import json
from test.fake_configs import DEFAULT_CONFIG_PATH
from typing import Any

from ankimorphs.ankimorphs_config import RawConfigFilterKeys, RawConfigKeys


def test_am_config_contains_keys() -> None:
    # This function loads the dict from 'config.json' and
    # removes all the attributes found in 'am_config' and checks
    # if anything was missed

    default_config_dict: dict[str, Any]

    with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as _file:
        default_config_dict = json.load(_file)

    assert len(default_config_dict) > 0

    custom_config_filter_attributes: list[str] = [
        _attr for _attr in dir(RawConfigFilterKeys) if _attr.startswith("__") is False
    ]
    custom_config_attributes: list[str] = [
        _attr for _attr in dir(RawConfigKeys) if _attr.startswith("__") is False
    ]

    assert len(custom_config_filter_attributes) > 0
    assert len(custom_config_attributes) > 0

    filter_keys = default_config_dict[RawConfigKeys.FILTERS][0].keys()
    config_keys = default_config_dict.keys()

    for filter_key in list(filter_keys):
        if filter_key.upper() in custom_config_filter_attributes:
            del default_config_dict[RawConfigKeys.FILTERS][0][filter_key]
        else:
            assert False

    assert len(default_config_dict[RawConfigKeys.FILTERS][0]) == 0

    for config_key in list(config_keys):
        if config_key.upper() in custom_config_attributes:
            del default_config_dict[config_key]
        else:
            assert False

    assert len(default_config_dict) == 0


def test_am_config_correct_values() -> None:
    # All the 'RawConfigKeys' and 'RawConfigFilterKeys' attributes should
    # just have the lowercase version of the attribute name as their value.

    for attr in dir(RawConfigKeys):
        if not attr.startswith("__") and attr.isupper():
            value = getattr(RawConfigKeys, attr)
            if value.upper() != attr:
                print(f"attr: {attr} is not upper of value: {value}")
                assert False

    for attr in dir(RawConfigFilterKeys):
        if not attr.startswith("__") and attr.isupper():
            value = getattr(RawConfigFilterKeys, attr)
            if value.upper() != attr:
                print(f"attr: {attr} is not upper of value: {value}")
                assert False
