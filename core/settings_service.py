import configparser
import os
import sys


def get_app_directory():
    if hasattr(sys, "_MEIPASS"):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


class SettingsService:

    DEFAULTS = {

        # Digital scales (Shtrih Print LAN COM)
        "DIGITAL_SCALES_INTERFACE": "com",
        "DIGITAL_SCALES_COM_PORT": "",
        "DIGITAL_SCALES_COM_BAUD": "9600",
        "DIGITAL_SCALES_COM_TIMEOUT": "1000",
        "DIGITAL_SCALES_IP_ADDRESS": "",
        "DIGITAL_SCALES_UDP_PORT": "0",
        "DIGITAL_SCALES_UDP_TIMEOUT": "1000",
        "DIGITAL_SCALES_PASSWORD": "",
        "DIGITAL_SCALES_FAST_LOAD": "0",
        "DIGITAL_SCALES_GROUP_CODE": "0",
    }

    def __init__(self):

        self.path = os.path.join(get_app_directory(), "settings.ini")

        self.config = configparser.ConfigParser()
        self.config.optionxform = str  # preserve case

        self._load()

    # ------------------------------------------------
    # Configuration status
    # ------------------------------------------------

    def is_configured(self) -> bool:

        required_keys = []

        for key in required_keys:
            value = self.get(key)
            if not value or not str(value).strip():
                return False

        return True

    # ------------------------------------------------
    # Internal load/save
    # ------------------------------------------------

    def _load(self):

        if not os.path.exists(self.path):

            self.config["DEFAULT"] = dict(self.DEFAULTS)
            self._save()

        else:

            self.config.read(self.path)

            # ensure new keys exist (for upgrades)
            updated = False

            for key, value in self.DEFAULTS.items():

                if key not in self.config["DEFAULT"]:
                    self.config["DEFAULT"][key] = value
                    updated = True

            if updated:
                self._save()

    def _save(self):

        with open(self.path, "w") as f:
            self.config.write(f)

    # ------------------------------------------------
    # Accessors
    # ------------------------------------------------

    def get(self, key: str, default=None):

        return self.config["DEFAULT"].get(key, default)

    def set(self, key: str, value: str):

        self.config["DEFAULT"][key] = str(value)
        self._save()

    # ------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------


    def is_digital_scales_configured(self) -> bool:
        interface = self.get("DIGITAL_SCALES_INTERFACE", "com").lower()

        if interface == "com":
            required_keys = [
                "DIGITAL_SCALES_COM_PORT",
                "DIGITAL_SCALES_COM_BAUD",
                "DIGITAL_SCALES_COM_TIMEOUT",
                "DIGITAL_SCALES_PASSWORD",
            ]
        else:
            required_keys = [
                "DIGITAL_SCALES_IP_ADDRESS",
                "DIGITAL_SCALES_UDP_PORT",
                "DIGITAL_SCALES_UDP_TIMEOUT",
                "DIGITAL_SCALES_PASSWORD",
            ]

        for key in required_keys:
            value = self.get(key)
            if not value or not str(value).strip():
                return False

        return True
