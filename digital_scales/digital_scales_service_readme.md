# Digital Scales Integration Service

This module hosts the COM bridge to the Shtrih Print LAN (“AddIn.DrvLP”) scales driver and exposes a FastAPI façade so the GUI service can control the scales without blocking the main thread.

## Components

1. **Configuration** (`core/settings_service.py`):
   * Settings for interface type (`com` vs `lan`), RS-232 port/baud/timeouts, UDP host/port, and driver password are stored in the shared settings service.
   * Default values (COM interface, 9600 baud, 1000 ms timeouts, empty password) are already registered so the settings dialog can persist overrides.

2. **Driver wrapper** (`digital_scales/shtrih_ptint_lan_com.py`):
   * `DigitalScalesConfig` reads the settings and validates whether enough information is configured for COM or LAN.
   * `ShtrihPtintLanComDriver` locates the Cyrillic/Latin COM properties/methods from the official description, sends `AddLD`, sets parameters (port, IP, password, etc.), activates the logical device, and performs operations such as connect/disconnect, health, clear database, upload products, and version reporting.
   * Uploading products follows the documented flow: `SetLoadMode` → `ClearGoodsDB` → `AddPLUData`/`WritePLUData` (branching to block mode for versions ≥ 3.0) → final `WritePLUDataBlock`/`ClearDataBlock` → `SetLoadMode(0)`.

3. **Async service** (`ws/service.py`):
   * `ComDigitalScalesService` wraps the driver in an `asyncio.Lock` and offloads every call to the GUI-thread COM executor to keep FastAPI non-blocking.
   * It exposes helpers for connect/disconnect/health/clear/upload/version and validates that the driver is configured before every operation.

4. **REST API** (`ws/routes.py`):
   * New endpoints under `/digital-scales` call the async service methods and translate exceptions into HTTP errors (503 when the driver isn’t ready, 500 for unexpected failures).
   * `DigitalScaleUploadRequest` accepts a list of PLU descriptors so you can push batches of products from POST payloads.

5. **Application wiring** (`ws/app.py` and `win_main.py`):
   * The FastAPI app now instantiates `ComDigitalScalesService` using the same COM executor as the fiscal driver when the digital scales settings are present.
   * Visibility of scales settings in the tray (TODO: extend the current dialog if needed) ensures the driver has credentials before the service starts.

## Data Flow

1. GUI writes settings (interface, port/IP, password).
2. Tray app starts, instantiates COM executors, driver, and FastAPI services.
3. REST requests `/digital-scales/upload` stream items to `ShtrihPtintLanComDriver.upload_products`, which configures the LU, clears the database, stages PLU entries, and flushes them in compliance with the official protocol.
4. Health or version probes reuse the connect/disconnect cycle per the specification, ensuring any in-flight connections are closed before returning status.

## Extensibility

* Additional endpoints (e.g., `clear`, `version`) already exist as helpers.
* You can extend the configuration to support UDP broadcast/ARP discovery if needed by exposing the relevant properties and the `TurnOnBroadcast`/`FinishBroadcast` methods defined in the driver description.

Keep this document in sync if the driver flow changes (different methods, new parameters, or expanded API surface).
