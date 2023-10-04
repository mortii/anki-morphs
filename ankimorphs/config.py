from aqt import mw


# TODO make a class
# TODO move get included models here
def get_config(key):
    config = mw.addonManager.getConfig(__name__)
    return config[key]


def get_default_config(key):
    addon = mw.addonManager.addonFromModule(__name__)  # necessary to prevent anki bug
    config = mw.addonManager.addonConfigDefaults(addon)
    return config[key]


def get_all_default_configs():
    addon = mw.addonManager.addonFromModule(__name__)  # necessary to prevent anki bug
    return mw.addonManager.addonConfigDefaults(addon)


def get_configs():
    return mw.addonManager.getConfig(__name__)


def update_configs(new_configs) -> None:
    print(f"update_preferences, _new_json_configs: {new_configs}")

    config = mw.addonManager.getConfig(__name__)

    for key, value in new_configs.items():
        config[key] = value
    mw.addonManager.writeConfig(__name__, config)
