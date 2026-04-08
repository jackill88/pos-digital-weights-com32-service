from .interfaces.app_service_interface import IApplicationService
from .database import Database
from .api_key_service import APIKeyService
from .settings_service import SettingsService


class ApplicationService(IApplicationService):

    def __init__(self):
        self.database = Database()
        self.settings = SettingsService()
        self.api_service = APIKeyService(self.database)

    def generate_api_key(self) -> str:
        new_key = self.api_service.generate_key()
        self.api_service.update_cache()
        return new_key

    def get_setting(self, key: str, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: str):
        self.settings.set(key, value)

    def validate_api_key(self, raw_key: str) -> bool:
        return self.api_service.validate_key(raw_key)