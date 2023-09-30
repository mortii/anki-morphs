from aqt import mw


def get_preference(key):
    config = mw.addonManager.getConfig(__name__)
    return config[key]


def get_preferences():
    return mw.addonManager.getConfig(__name__)


def update_preferences(_new_json_configs) -> None:
    print(f"update_preferences, _new_json_configs: {_new_json_configs}")

    config = mw.addonManager.getConfig(__name__)

    for key, value in _new_json_configs.items():
        config[key] = value
    mw.addonManager.writeConfig(__name__, config)
