import os
import sys
import threading
import logging
import pythoncom
import win32com.client
import uvicorn
import wx
import wx.adv

from ws.app import create_app
from core.app_service import ApplicationService
from digital_scales.shtrih_print_lan_com import DigitalScalesConfig, ShtrihPtintLanComDriver
from utils import resource_path, get_app_directory


# =============================
# COM EXECUTOR (GUI THREAD - same thread for Fastapi and STA threads)
# =============================

class COMExecutor:
    """
    Thread-safe COM call executor for STA COM objects.
    Use call(func, *args, timeout=...) to safely call COM objects from any thread.
    """
    def __init__(self, com_object):
        self.com_object = com_object
        self._default_timeout = 90.0
        self._lock = threading.Lock()

    def call(self, func, *args, timeout=None):
        """
        Calls a COM function in a thread-safe way with timeout.
        This can be called from any thread.
        """
        effective_timeout = self._default_timeout if timeout is None else max(1.0, float(timeout))
        packet = {
            "func": func,
            "args": args,
            "event": threading.Event(),
            "result": None,
            "error": None,
        }

        # Execute in the main thread (STA) with pythoncom.CoInitialize if needed
        thread = threading.Thread(target=self._execute, args=(packet,))
        thread.start()
        completed = packet["event"].wait(effective_timeout)

        if not completed:
            func_name = getattr(func, "__name__", repr(func))
            raise TimeoutError(f"COM call timed out after {effective_timeout:.1f}s ({func_name})")

        if packet["error"] is not None:
            raise packet["error"]
        return packet["result"]

    def _execute(self, packet):
        """
        Executes the COM function safely.
        """
        try:
            if not pythoncom.CoInitialize():
                pythoncom.CoInitialize()
            packet["result"] = packet["func"](*packet["args"])
        except Exception as e:
            packet["error"] = e
        finally:
            packet["event"].set()


class APIServerThread(threading.Thread):
    def __init__(
        self,
        digital_scales_executor,
        digital_scales_driver,
        app_service,
    ):
        super().__init__(daemon=True)
        self.server = None
        self.digital_scales_executor = digital_scales_executor
        self.digital_scales_driver = digital_scales_driver
        self.app_service = app_service

    def run(self):
        app = create_app(
            self.digital_scales_executor,
            self.digital_scales_driver,
            self.app_service,
        )

        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8001,
            workers=1,
            log_config=None,
        )

        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


# 🔹 Log window and emitter for wxPython
class LogWindow(wx.Frame):
    def __init__(self, parent=None, title="Fiscal Service Logs"):
        super().__init__(parent, title=title, size=(800, 400))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.text_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(sizer)

    def append_log(self, message):
        wx.CallAfter(self.text_ctrl.AppendText, message + "\n")


class LogEmitter(logging.Handler):
    def __init__(self, log_window: LogWindow):
        super().__init__()
        self.log_window = log_window

    def emit(self, record):
        msg = self.format(record)
        self.log_window.append_log(msg)


def setup_logging(log_window: LogWindow):
    log_dir = get_app_directory()
    log_path = os.path.join(log_dir, "app.log")

    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    gui_handler = LogEmitter(log_window)
    gui_handler.setFormatter(formatter)
    root_logger.addHandler(gui_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.info("Logging initialized")


# ---- Tray Icon ----
class MyTaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, app):
        super().__init__()
        self.app = app
        icon = wx.Icon(resource_path("icon.ico"), wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon, "ODOO Fiscal Service Integration")
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.on_show_logs)


    def CreatePopupMenu(self):
        menu = wx.Menu()
        
        # Add menu items
        show_logs_id = wx.NewIdRef()
        settings_id = wx.NewIdRef()
        api_key_id = wx.NewIdRef()
        reboot_id = wx.NewIdRef()
        exit_id = wx.NewIdRef()
        
        menu.Append(show_logs_id, "Show Logs")
        menu.Append(settings_id, "Configure device settings...")
        menu.Append(api_key_id, "Generate API Key")
        menu.Append(reboot_id, "Reinit device")
        menu.Append(exit_id, "Exit")

        # Bind events using wx.EVT_MENU
        self.Bind(wx.EVT_MENU, lambda e: self.app.show_logs(), id=show_logs_id)
        self.Bind(wx.EVT_MENU, lambda e: self.app.show_settings(), id=settings_id)
        self.Bind(wx.EVT_MENU, lambda e: self.app.generate_api_key(), id=api_key_id)
        self.Bind(wx.EVT_MENU, lambda e: self.app.reboot_scales_service(), id=reboot_id)
        self.Bind(wx.EVT_MENU, lambda e: self.app.exit_app(), id=exit_id)

        return menu

    def on_show_logs(self, event):
        self.app.show_logs()

    def on_show_settings(self, event):
        self.app.show_settings()

    def on_generate_api_key(self, event):
        self.app.generate_api_key()

    def on_reboot_scales(self, event):
        self.app.reboot_scales_service()

    def on_exit(self, event):
        self.app.exit_app()


# Settings dialog
class SetupDialog(wx.Dialog):
    def __init__(self, settings_service):
        super().__init__(None, title="Initial Configuration", size=(500, 600))
        self.settings = settings_service

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Digital scales group
        gb = wx.StaticBox(panel, label="Digital scales (Shtrih Print LAN/COM)")
        sbsizer = wx.StaticBoxSizer(gb, wx.VERTICAL)
        fg = wx.FlexGridSizer(0, 2, 5, 5)

        self.ds_interface = wx.ComboBox(panel, choices=["com", "lan"])
        self.ds_interface.SetValue(self.settings.get("DIGITAL_SCALES_INTERFACE", "com"))
        self.ds_com_port = wx.TextCtrl(panel, value=self.settings.get("DIGITAL_SCALES_COM_PORT", ""))
        self.ds_baud = wx.TextCtrl(panel, value=self.settings.get("DIGITAL_SCALES_COM_BAUD", "9600"))
        self.ds_timeout = wx.TextCtrl(panel, value=self.settings.get("DIGITAL_SCALES_COM_TIMEOUT", "1000"))
        self.ds_ip_address = wx.TextCtrl(panel, value=self.settings.get("DIGITAL_SCALES_IP_ADDRESS", ""))
        self.ds_udp_port = wx.TextCtrl(panel, value=self.settings.get("DIGITAL_SCALES_UDP_PORT", ""))
        self.ds_udp_timeout = wx.TextCtrl(panel, value=self.settings.get("DIGITAL_SCALES_UDP_TIMEOUT", "1000"))
        self.ds_password = wx.TextCtrl(panel, value=self.settings.get("DIGITAL_SCALES_PASSWORD", ""), style=wx.TE_PASSWORD)
        self.ds_fast_load = wx.CheckBox(panel, label="Fast load mode")
        self.ds_fast_load.SetValue(self.settings.get("DIGITAL_SCALES_FAST_LOAD", "0").lower() in ("1", "true", "yes"))
        self.ds_group_code = wx.TextCtrl(panel, value=self.settings.get("DIGITAL_SCALES_GROUP_CODE", "0"))

        fg.AddMany([
            (wx.StaticText(panel, label="Interface:"), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_interface,
            (wx.StaticText(panel, label="COM port:"), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_com_port,
            (wx.StaticText(panel, label="Baud rate:"), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_baud,
            (wx.StaticText(panel, label="Timeout (ms):"), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_timeout,
            (wx.StaticText(panel, label="IP address:"), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_ip_address,
            (wx.StaticText(panel, label="UDP port:"), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_udp_port,
            (wx.StaticText(panel, label="UDP timeout (ms):"), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_udp_timeout,
            (wx.StaticText(panel, label="Password:"), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_password,
            (wx.StaticText(panel, label=""), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_fast_load,
            (wx.StaticText(panel, label="Group code:"), 0, wx.ALIGN_CENTER_VERTICAL), self.ds_group_code,
        ])
        sbsizer.Add(fg, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(sbsizer, 0, wx.EXPAND | wx.ALL, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        save_btn = wx.Button(panel, label="Save Configuration")
        cancel_btn = wx.Button(panel, label="Exit")
        save_btn.Bind(wx.EVT_BUTTON, self.save)
        cancel_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        btn_sizer.AddStretchSpacer()
        btn_sizer.Add(save_btn)
        btn_sizer.Add(cancel_btn, 0, wx.LEFT, 5)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(main_sizer)
        self.toggle_interface(self.ds_interface.GetValue())
        self.ds_interface.Bind(wx.EVT_COMBOBOX, lambda e: self.toggle_interface(self.ds_interface.GetValue()))

    def toggle_interface(self, value):
        is_com = value.lower() == "com"
        self.ds_com_port.Enable(is_com)
        self.ds_baud.Enable(is_com)
        self.ds_timeout.Enable(is_com)
        self.ds_ip_address.Enable(not is_com)
        self.ds_udp_port.Enable(not is_com)
        self.ds_udp_timeout.Enable(not is_com)

    def save(self, event):
        self.settings.set("DIGITAL_SCALES_INTERFACE", self.ds_interface.GetValue().lower())
        self.settings.set("DIGITAL_SCALES_COM_PORT", self.ds_com_port.GetValue().strip())
        self.settings.set("DIGITAL_SCALES_COM_BAUD", self.ds_baud.GetValue().strip())
        self.settings.set("DIGITAL_SCALES_COM_TIMEOUT", self.ds_timeout.GetValue().strip())
        self.settings.set("DIGITAL_SCALES_IP_ADDRESS", self.ds_ip_address.GetValue().strip())
        self.settings.set("DIGITAL_SCALES_UDP_PORT", self.ds_udp_port.GetValue().strip())
        self.settings.set("DIGITAL_SCALES_UDP_TIMEOUT", self.ds_udp_timeout.GetValue().strip())
        self.settings.set("DIGITAL_SCALES_PASSWORD", self.ds_password.GetValue().strip())
        self.settings.set("DIGITAL_SCALES_FAST_LOAD", self.ds_fast_load.GetValue())
        self.settings.set("DIGITAL_SCALES_GROUP_CODE", self.ds_group_code.GetValue().strip())
        self.Close()

# =============================
# Dialogs etc..
# =============================

class APIKeyDialog(wx.Dialog):
    def __init__(self, api_key):
        super().__init__(None, title="New API Key", size=(400, 150))
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Info text
        info = wx.StaticText(panel, label="This API key will NOT be shown again.\nCopy and store it securely.")
        sizer.Add(info, 0, wx.ALL | wx.EXPAND, 10)

        # Read-only text field for API key
        self.key_ctrl = wx.TextCtrl(panel, value=api_key, style=wx.TE_READONLY)
        sizer.Add(self.key_ctrl, 0, wx.ALL | wx.EXPAND, 10)

        # Buttons: Copy + Close
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(panel, label="Copy")
        close_btn = wx.Button(panel, label="Close")
        btn_sizer.Add(copy_btn)
        btn_sizer.AddSpacer(10)
        btn_sizer.Add(close_btn)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        panel.SetSizer(sizer)

        # Event bindings
        copy_btn.Bind(wx.EVT_BUTTON, self.on_copy)
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())

    def on_copy(self, event):
        """Copy the API key to the clipboard"""
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.key_ctrl.GetValue()))
            wx.TheClipboard.Close()
            wx.MessageBox("API key copied to clipboard!", "Copied", wx.OK | wx.ICON_INFORMATION)

# =============================
# Main Tray App
# =============================
class TrayApp:
    def __init__(self):
        self.app_service = ApplicationService()
        self.app = wx.App(False)
        self.log_window = LogWindow()
        setup_logging(self.log_window)
        self.tray_icon = MyTaskBarIcon(self)

        if not self.app_service.settings.is_configured():
            dlg = SetupDialog(self.app_service.settings)
            dlg.ShowModal()
            dlg.Destroy()
            if not self.app_service.settings.is_configured():
                sys.exit(0)

        self._pythoncom_initialized = False
        self.start_scales_device_driver()

    def start_scales_device_driver(self):
        digital_scales_ready = self.app_service.settings.is_digital_scales_configured()
        needs_com = digital_scales_ready
        
        if needs_com and not self._pythoncom_initialized:
            pythoncom.CoInitialize()
            self._pythoncom_initialized = True


        self.digital_scales_com_object = None
        self.digital_scales_driver = None
        self.digital_scales_executor = None

        if digital_scales_ready:
            try:
                self.digital_scales_com_object = win32com.client.Dispatch("AddIn.DrvLP")
                self.digital_scales_driver = ShtrihPtintLanComDriver(
                    self.digital_scales_com_object,
                    DigitalScalesConfig(self.app_service.settings),
                )
                self.digital_scales_executor = COMExecutor(self.digital_scales_com_object)
                logging.info("Digital scales driver initialized")
            except Exception as exc:
                logging.exception("Digital scales driver initialization failed")
                self.digital_scales_com_object = None
                self.digital_scales_driver = None
                self.digital_scales_executor = None
        else:
            logging.info("Digital scales driver skipped: not configured")


        self.api_thread = APIServerThread(
            self.digital_scales_executor,
            self.digital_scales_driver,
            self.app_service,
        )
        self.api_thread.start()

    # ... COMExecutor, APIServerThread remain unchanged ...

    def show_logs(self):
        self.log_window.Show()
        self.log_window.Raise()

    def show_settings(self):
        dlg = SetupDialog(self.app_service.settings)
        dlg.ShowModal()
        dlg.Destroy()

    def generate_api_key(self):
        key = self.app_service.generate_api_key()
        dlg = APIKeyDialog(key)
        dlg.ShowModal()
        dlg.Destroy()

    def run(self):
        self.app.MainLoop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    TrayApp().run()