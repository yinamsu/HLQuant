import asyncio
import aiohttp
import json

async def main():
    resolver = aiohttp.ThreadedResolver()
    connector = aiohttp.TCPConnector(resolver=resolver)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post("https://api.hyperliquid-testnet.xyz/info", json={"type": "spotMetaAndAssetCtxs"}) as response:
            data = await response.json()
            print(json.dumps(data[0]['universe'][:5], indent=2))
            print("---")
            print(json.dumps(data[0]['tokens'][:5], indent=2))

asyncio.run(main())
