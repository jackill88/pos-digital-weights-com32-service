import asyncio


class ComDigitalScalesService:
    def __init__(self, com_executor, digital_scales_driver):
        self.com_executor = com_executor
        self.digital_scales_driver = digital_scales_driver
        self.lock = asyncio.Lock()

    def is_configured(self) -> bool:
        return bool(self.com_executor and self.digital_scales_driver)

    async def _run(self, func, *args):
        if not self.is_configured():
            raise RuntimeError("Digital scales driver is not configured")

        async with self.lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.com_executor.call(func, *args),
            )

    async def connect(self):
        return await self._run(self.digital_scales_driver.connect)

    async def disconnect(self):
        return await self._run(self.digital_scales_driver.disconnect)

    async def health(self):
        return await self._run(self.digital_scales_driver.health)

    async def clear_database(self):
        return await self._run(self.digital_scales_driver.clear_database)

    async def upload_products(self, products, partial=False):
        return await self._run(self.digital_scales_driver.upload_products, products, partial)

    async def version(self):
        return await self._run(self.digital_scales_driver.get_version)

