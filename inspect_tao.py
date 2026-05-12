import asyncio
import aiohttp
import json

async def main():
    resolver = aiohttp.ThreadedResolver()
    connector = aiohttp.TCPConnector(resolver=resolver)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post("https://api.hyperliquid-testnet.xyz/info", json={"type": "metaAndAssetCtxs"}) as response:
            data = await response.json()
            meta, ctxs = data
            for i, asset in enumerate(meta['universe']):
                if asset['name'] == 'TAO':
                    print(json.dumps(ctxs[i], indent=2))
                    break

asyncio.run(main())
