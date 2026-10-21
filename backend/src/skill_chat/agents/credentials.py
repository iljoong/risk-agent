from collections.abc import Awaitable, Callable

from azure.identity.aio import DefaultAzureCredential


class Credentials:
    def __init__(self):
        self.credential = DefaultAzureCredential()

    def provider(self, scope: str) -> Callable[[], Awaitable[str]]:
        async def acquire() -> str:
            return (await self.credential.get_token(scope)).token

        return acquire

    async def close(self) -> None:
        await self.credential.close()
