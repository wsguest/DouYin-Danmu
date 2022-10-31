import json
import asyncio
import websockets
import logging
from playwright.async_api import async_playwright

clients = set() # 客户端
debug = True # 调试状态

# 日志输出设置
logger = logging.getLogger("ws_hub")
logger.setLevel("DEBUG" if debug else "INFO")
fmt_str = "%(levelname)1.1s [%(asctime)s] %(message)s"
fmt = logging.Formatter(fmt=fmt_str, datefmt=None)
handler_console = logging.StreamHandler()
handler_console.setFormatter(fmt)
logger.addHandler(handler_console)

# websocket 服务
async def handler(websocket, path):
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)

# 广播消息
async def broadcast_message(msg: dict):
    logger.debug(msg)
    data = json.dumps(msg)
    for c in clients:
        await c.send(data)
    return ""

# 注入代码，先隐藏播放器，再监听聊天栏
# 以抖音为例其他平台做对应修改
script = """
document.querySelector('.basicPlayer').remove();
const targetNode = document.getElementsByClassName('webcast-chatroom___items')[0].firstChild;
const callback = function(mutationsList, observer) {
    for(const mutation of mutationsList) {
            if(mutation.addedNodes.length > 0) {
                const node = mutation.addedNodes[0].firstChild;
                if(node.childNodes.length < 2)
                    continue;
                const name = node.childNodes[1].innerText;
                const content = node.lastChild.innerText;
                console.log(name + ': ' + content);
                window.on_message({data:{nickname:name, content:content, uid:0, senderlevel:10}, timestamp:0});
            }
        }
    };
    
const config = {attributes: false, childList: true, subtree: true, characterData: false};
const observer = new MutationObserver(callback);
observer.observe(targetNode, config);
"""

# 启动浏览器
async def pw_douyin(room_id):
    url = f"https://live.douyin.com/{room_id}"
    check_interval = 5
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not debug, channel="msedge")
        context = await browser.new_context()
        await context.expose_function("on_message", broadcast_message)
        page = await context.new_page()
        while True:
            if page.is_closed() or page.url != url:
                if page.is_closed():
                    page = await context.new_page()
                await page.goto(url)
                await page.evaluate(script)

            await asyncio.sleep(check_interval)
            await broadcast_message({"state": "alive", "interval": check_interval})

# 运行hub
def run_hub_forever(ws_port, room_id):
    try:
        ws_future = websockets.serve(handler, "localhost", ws_port)
        douyin_future = pw_douyin(room_id)
        logger.info(f"Hub server listen at: {ws_port}")
        asyncio.gather(douyin_future, ws_future)
        asyncio.get_event_loop().run_forever()
    except Exception as ex:
        logger.error(f"Hub server exception: {ex}")


if __name__ == "__main__":
    room = "918495818136"  # douyin room id
    port = 88  #  websocket port
    run_hub_forever(port, room)
