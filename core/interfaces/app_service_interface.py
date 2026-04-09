from abc import ABC, abstractmethod


class IApplicationService(ABC):

    @abstractmethod
    def generate_api_key(self) -> str:
        pass

    @abstractmethod
    def get_setting(self, key: str, default=None):
        pass

    @abstractmethod
    def set_setting(self, key: str, value: str):
        pass