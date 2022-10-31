import asyncio
import websockets

async def test():
    async with websockets.connect('ws://localhost:88') as websocket:
        while True:
            msg = await websocket.recv()
            print(f"{msg}")

asyncio.get_event_loop().run_until_complete(test())
