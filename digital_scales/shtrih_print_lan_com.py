import datetime
from decimal import Decimal
from typing import Sequence, Optional, Any
import logging

import pywintypes

from core.settings_service import SettingsService
from digital_scales.models import DigitalScaleItem

logger = logging.getLogger(__name__)


class DigitalScalesDriverError(Exception):
    """Raised when the scales driver returns an error or is misconfigured."""


class DigitalScalesConfig:
    """Configuration holder for the Shtrih Print LAN COM integration."""

    def __init__(self, settings: SettingsService):
        raw_interface = settings.get("DIGITAL_SCALES_INTERFACE", "com") or "com"
        self.interface = raw_interface.strip().lower()
        if self.interface not in ("com", "lan", "udp"):
            self.interface = "com"

        self.com_port = settings.get("DIGITAL_SCALES_COM_PORT", "").strip()
        self.baud_rate = self._to_int(settings.get("DIGITAL_SCALES_COM_BAUD", "9600"), 9600)
        self.com_timeout = self._to_int(settings.get("DIGITAL_SCALES_COM_TIMEOUT", "1000"), 1000)
        self.ip_address = settings.get("DIGITAL_SCALES_IP_ADDRESS", "").strip()
        self.udp_port = self._to_int(settings.get("DIGITAL_SCALES_UDP_PORT", "0"), 0)
        self.udp_timeout = self._to_int(settings.get("DIGITAL_SCALES_UDP_TIMEOUT", "1000"), 1000)
        self.password = settings.get("DIGITAL_SCALES_PASSWORD", "").strip()
        self.fast_load = settings.get("DIGITAL_SCALES_FAST_LOAD", "0").strip() in ("1", "true", "True")
        self.group_code = settings.get("DIGITAL_SCALES_GROUP_CODE", "0").strip()

    @staticmethod
    def _to_int(value: Optional[str], default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @property
    def interface_code(self) -> int:
        return 0 if self.interface == "com" else 1

    def is_configured(self) -> bool:
        if self.interface == "com":
            return bool(self.com_port and self.password)
        return bool(self.ip_address and self.udp_port and self.password)


PROPERTY_NAMES = {
    "ld_number": ("LDNumber",),
    "interface": ("LDInterface",),
    "password": ( "Password",),
    "com_port": ("LDCOmNumber",),
    "baud_rate": ("LDBaudRate",),
    "timeout": ("ТаймаутЛУ", "Timeout"),
    "ip_address": ("LDRemoteHost",),
    "udp_port": ("LDRemotePort", ),
    "udp_timeout": ("LDTimeoutUDP", ),
    "fast_load": ("QuickLoadON",),
    "ld_index": ("ИндексЛУ", "LDIndex"),
    "result": ("Результат", "Result"),
    "result_description": ("ОписаниеРезультата", "ResultDescription"),
    "version_ke": ("VersionLP", ),
    "version_file_st": ("ВерсияФайлаСТ", "VersionFileST"),
    "version_file_ml": ("ВерсияФайлаМЛ", "VersionFileML"),
    "plu_number": ("НомерПЛУ", "PLUNumber"),
    "name_first": ("ПервоеНаименованиеТовара", "NameFirst"),
    "name_second": ("ВтороеНаименованиеТовара", "NameSecond"),
    "tare": ("Тара", "Tare"),
    "shelf_life": ("СрокХранения", "ShelfLife"),
    "sell_by_date": ("ДатаРеализации", "SellByDate"),
    "price": ("Цена", "Price"),
    "group_code": ("ГрупповойКод", "GroupCode"),
    "item_code": ("КодТовара", "ItemCode"),
    "message_number": ("НомерСообщения", "MessageNumber"),
    "image_number": ("PictureNumber",),
    "mid_code": ("ROSTEST",),
    "goods_type": ("GoodsType",),
    "weight_prefix": ("ВесовойПрефиксШК", "WeightBarcodePrefix"),
    "piece_prefix": ("ШтучныйПрефиксШК", "PieceBarcodePrefix"),
    "price_include_vat": ("ЦенаВключаетПДВ", "PriceIncludesVAT"),
    "plu_block_result": ("РезультатПЛУ", "PLUResult"),
    "connected": ("Connected",),
}

METHOD_NAMES = {
    "add_lu": ("AddLD",),
    "set_parameters": ("SetParamLD",),
    "get_active": ("GetActiveLD",),
    "set_active": ("SetActiveLD",),
    "connect": ("Connect",),
    "disconnect": ("Disconnect",),
    "enumerate": ("EnumLD",),
    "delete_lu": ("DeleteLD",),
    "set_load_mode": ("SetLoadMode",),
    "clear_goods": ("ClearGoodsDB",),
    "clear_data_block": ("ClearBlock",),
    "add_plu_data": ("AddPLUToBlock",),
    "write_block": ("SetPLUBlockData",),
    "write_plu": ("SetPLUData",),
    "beep": ("Beep",)
}


class ShtrihPtintLanComDriver:
    def __init__(self, com_object, config: DigitalScalesConfig):
        self._driver = com_object
        self._config = config
        self._device_id: Optional[int] = None

    def _set_property(self, key: str, value: Any):
        names = PROPERTY_NAMES.get(key, ())
        last_exc: Optional[Exception] = None
        for name in names:
            try:
                setattr(self._driver, name, value)
                return
            except (AttributeError, pywintypes.com_error) as exc:
                last_exc = exc
                continue
        raise DigitalScalesDriverError(f"Unable to set COM property {key} ({names}): {last_exc}")

    def _get_property(self, key: str, default: Any = None) -> Any:
        names = PROPERTY_NAMES.get(key, ())
        last_exc: Optional[Exception] = None
        for name in names:
            try:
                return getattr(self._driver, name)
            except (AttributeError, pywintypes.com_error) as exc:
                last_exc = exc
                continue
        if default is not None:
            return default
        raise DigitalScalesDriverError(f"Unable to read COM property {key} ({names}): {last_exc}")

    def _call_method(self, key: str, *args, **kwargs) -> Any:
        names = METHOD_NAMES.get(key, ())
        last_exc: Optional[Exception] = None
        for name in names:
            try:
                method = getattr(self._driver, name)
            except (AttributeError, pywintypes.com_error) as exc:
                last_exc = exc
                continue
            return method(*args, **kwargs)
        raise DigitalScalesDriverError(f"COM method {key} not found ({names}): {last_exc}")

    def _ensure_configured(self):
        if not self._config.is_configured():
            raise DigitalScalesDriverError("Digital scales configuration is incomplete.")

    def _apply_connection_parameters(self):
        self._set_property("interface", 0 if self._config.interface=="com" else 1)
        if self._config.interface == 'com':
            self._set_property("com_port", self._config.com_port)
            self._set_property("timeout", self._config.com_timeout)
        else:
            self._set_property("ip_address", self._config.ip_address)
            self._set_property("udp_port", self._config.udp_port)
            self._set_property("udp_timeout", self._config.udp_timeout)
        
        self._set_property("password", self._config.password)

        self._call_method("set_parameters") 



    def connect(self) -> dict:
        self._ensure_configured()

        if self._device_id is not None:
            try:
                self.disconnect()
            except DigitalScalesDriverError:
                raise
        
        self._call_method("get_active")
        device_id = self._get_property("ld_number", default=None)
        if device_id is None:
            self._call_method("add_lu")   
            device_id = self._get_property("ld_number", default=None)
            logger.info(f"Added new LU ({device_id}) because no active LU was found.")


        device_id = self._get_property("ld_number", default=None)
        if device_id is None:
            raise DigitalScalesDriverError("Unable to read logical device number after adding LU.")
        self._device_id = int(device_id)
        self._apply_connection_parameters()
        self._call_method("set_active")

        self._call_method("connect")

        self._call_method("beep")

        _connected = self._get_property("connected")
        if not _connected:
            raise DigitalScalesDriverError("Driver is initialized but the device is not connected.")

        return {"status": "ok", "device_id": self._device_id}

    def _activate_and_connect(self) -> dict:
        return self.connect()

    def _disconnect_connection(self):
        try:
            self._call_method("disconnect")
        except DigitalScalesDriverError:
            pass

    def disconnect(self) -> dict:
        if self._device_id is None:
            return {"status": "ok", "message": "Device was not connected."}

        self._set_property("ld_number", self._device_id)
        self._call_method("set_active")
        self._call_method("disconnect")
        self._set_property("ld_index", 0)
        self._call_method("enumerate")
        self._call_method("set_active")
        self._set_property("ld_number", self._device_id)
        self._call_method("delete_lu")

        self._device_id = None

        return {"status": "ok"}

    def check_connection(self) -> dict:
        if self._device_id is None:
            raise DigitalScalesDriverError("Device is not connected.")

        try:
            self._activate_and_connect()
        finally:
            self._disconnect_connection()

        return {"status": "ok"}

    def clear_database(self) -> dict:

        try:
            self._activate_and_connect()

            if self._device_id is None:
                raise DigitalScalesDriverError("Device is not connected.")
            
            result = int(self._call_method("clear_goods") or 0)
            if result != 0:
                raise DigitalScalesDriverError(f"Device returned {result} when clearing goods.")
        finally:
            self._disconnect_connection()

        return {"status": "ok"}

    def get_version(self) -> dict:

        self._activate_and_connect()

        try:
            driver_version = self._get_property("version_ke", default=0)
        except (ValueError, TypeError):
            driver_version = "Unknown"

        return {"status": "ok", "driver_version": driver_version}

    def _prepare_names(self, item: DigitalScaleItem) -> tuple[str, str]:
        value = (item.full_name or item.name or "").strip()
        if not value:
            value = "(unnamed)"
        first = value[:28]
        second = value[28:56]
        return first, second

    def _compute_code(self, item: DigitalScaleItem) -> int:
        code = item.code
        if code:
            return int(code)
        barcode = item.barcode
        if barcode and len(barcode) >= 8:
            return int(barcode[2:8])
        return int(item.plu)

    def _set_price(self, amount: Decimal):
        formatted = f"{amount.quantize(Decimal('0.01'))}"
        self._set_property("price", formatted)

    def _write_item(self, item: DigitalScaleItem) -> None:
        first, second = self._prepare_names(item)
        self._set_property("plu_number", int(item.plu))
        self._set_property("name_first", first)
        self._set_property("name_second", second)
        self._set_property("tare", 0)
        shelf_life = int(item.shelf_life or 0)
        self._set_property("shelf_life", shelf_life)
        # if shelf_life > 0:
        #     self._set_property("sell_by_date", datetime.datetime(2001, 1, 1))
        # else:
        #     self._set_property("sell_by_date", 0)
        self._set_price(item.price)
        self._set_property("group_code", self._config.group_code or "0")
        self._set_property("item_code", self._compute_code(item))
        self._set_property("message_number", 0)
        self._set_property("image_number", 0)
        self._set_property("mid_code", " ")
        self._set_property("goods_type", item.goods_type or 0)

        version = self._get_property("version_ke", default=0)
        try:
            version = float(version)
        except (TypeError, ValueError):
            version = 0.0

        if version >= 3.0:
            self._call_method("add_plu_data")
            result = int(self._get_property("result", default=0))
            if result == -21:
                if int(self._call_method("write_block") or 0) != 0:
                    raise DigitalScalesDriverError("Failed to flush PLU block.")
                self._call_method("clear_data_block")
                self._call_method("add_plu_data")
        else:
            if int(self._call_method("write_plu") or 0) != 0:
                raise DigitalScalesDriverError("Failed to write PLU entry.")

    def _begin_upload(self) -> None:
        try:
            self._call_method("set_load_mode")
        except DigitalScalesDriverError:
            pass

        if int(self._call_method("clear_goods") or 0) != 0:
            raise DigitalScalesDriverError("Unable to clear goods database before upload.")

        self._set_property("fast_load", 1 if self._config.fast_load else 0)
        try:
            self._call_method("set_load_mode")
        except DigitalScalesDriverError:
            pass

    def _finish_upload(self) -> None:
        version = self._get_property("version_ke", default=0)
        try:
            version = float(version)
        except (TypeError, ValueError):
            version = 0.0

        if version >= 3.0:
            if int(self._call_method("write_block") or 0) != 0:
                raise DigitalScalesDriverError("Failed to flush PLU block after upload.")
            self._call_method("clear_data_block")


        self._set_property("fast_load", 0)
        try:
            self._call_method("set_load_mode")
        except DigitalScalesDriverError:
            pass

    def upload_products(
        self,
        products: Sequence[DigitalScaleItem],
        partial: bool = False,
    ) -> dict:
        
        self._activate_and_connect()

        if self._device_id is None:
            raise DigitalScalesDriverError("Device is not connected.")
        if not products:
            raise DigitalScalesDriverError("Products list is empty.")

        try:
            if not partial:
                self._begin_upload()

            for product in products:
                self._write_item(product)

            if not partial:
                self._finish_upload()
        finally:
            self._disconnect_connection()

        return {"status": "ok", "uploaded": len(products)}

    def health(self) -> dict:
        try:
            self._activate_and_connect()
        finally:
            self._disconnect_connection()

        return {"status": "ok"}
