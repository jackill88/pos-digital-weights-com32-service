from abc import ABC, abstractmethod
from typing import Dict, Any

import threading
import logging
from typing import Callable, Dict, Any

import pythoncom



class FiscalDriver(ABC):

    @abstractmethod
    def configure(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def open_shift(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def close_shift(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def service_input(self, amount: float) -> Dict[str, Any]:
        pass

    @abstractmethod
    def service_output(self, amount: float) -> Dict[str, Any]:
        pass

    @abstractmethod
    def x_report(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def fiscal_receipt(
        self,
        json_str_goods: str,
        json_str_payments: str,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def fiscal_receipt_return(
        self,
        original_receipt_fiscal_id: str,
        json_str_goods: str,
        json_str_payments: str,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_last_error(self) -> Dict[str, Any]:
        pass


class BaseFiscalDriver:

    def __init__(self):

        self.reboot_delay = None

        # Fiscal devices must run sequentially
        self._lock = threading.RLock()

        # Optional logger
        self._logger = logging.getLogger(self.__class__.__name__)

        # COM initialization flag
        self._com_initialized = False

    # ------------------------------------------------
    # COM Initialization
    # ------------------------------------------------

    def _ensure_com(self):
        if not self._com_initialized:
            pythoncom.CoInitialize()
            self._com_initialized = True

    # ------------------------------------------------
    # Safe execution wrapper
    # ------------------------------------------------

    def _safe_call(self, fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:

        with self._lock:

            try:

                self._ensure_com()

                result = fn()

                if not isinstance(result, dict):
                    return {
                        "status": "error",
                        "message": "Driver returned invalid response",
                    }

                return result

            except Exception as e:

                self._logger.exception("Fiscal driver error")

                try:
                    # try getting the extended description
                    response_text = f": {e.response.text}"
                except:
                    response_text = ""

                return {
                    "status": "error",
                    "message": f"{str(e)}{response_text}",
                }

    # ------------------------------------------------
    # Standard response helpers
    # ------------------------------------------------

    def _ok(self, **kwargs) -> Dict[str, Any]:

        payload = {"status": "ok"}

        if kwargs:
            payload.update(kwargs)

        return payload

    def _error(self, message: str) -> Dict[str, Any]:

        return {
            "status": "error",
            "message": message,
        }