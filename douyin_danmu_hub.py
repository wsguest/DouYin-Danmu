import json
import asyncio
import websockets
import logging
from playwright.async_api import async_playwright

clients = set()  # 客户端
debug = True  # 调试状态

# 日志输出设置
logger = logging.getLogger("ws_hub")
logger.setLevel("DEBUG" if debug else "INFO")
fmt_str = "%(levelname)1.1s [%(asctime)s] %(message)s"
fmt = logging.Formatter(fmt=fmt_str, datefmt=None)
handler_console = logging.StreamHandler()
handler_console.setFormatter(fmt)
logger.addHandler(handler_console)


# websocket 服务
async def ws_handler(websocket, path):
    logger.info(f"Client connected {websocket.remote_address[0]}:{websocket.remote_address[1]}{path}")
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


# 注入的代码，先隐藏播放器，再监听聊天栏 以抖音为例其他平台做对应修改
script_douyin = """
    document.querySelector('.basicPlayer').remove(); // 隐藏播放器
    const chat_list = document.getElementsByClassName('webcast-chatroom___items')[0].firstChild;
    const observer = new MutationObserver((mutationsList, observer) => {
        for(const mutation of mutationsList) {
                if(mutation.addedNodes.length > 0) {
                    const node = mutation.addedNodes[0].firstChild;
                    if(node.childNodes.length < 3)
                        continue;
                    const level = node.firstChild.innerHTML.match(/user_grade_level_v5_(\d+)\.png/i)[1]
                    const name = node.childNodes[1].innerText;
                    const content = node.lastChild.innerText;
                    // windows.host_callback 为保留函数名称，要与callback_name保持一致，参数成员可以根据需要任意修改
                    window.host_callback({data:{nickname:name, content:content, uid:0, level:level}, timestamp:0});
                }
            }
        });
    const config = {attributes: false, childList: true, subtree: true, characterData: false};
    observer.observe(chat_list, config);
    """
callback_name = "on_message"  # 回调函数签名，用于浏览器和代码通信
script_douyin = script_douyin.replace("host_callback", callback_name)

# 启动浏览器，打开直播间，注入代码
async def open_room(room_url, javascript):
    check_interval = 5
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not debug, channel="msedge")  # 启动Edge浏览器
        context = await browser.new_context()
        await context.expose_function(callback_name, broadcast_message)
        page = await context.new_page()
        while True:
            if page.is_closed() or page.url != room_url:
                if page.is_closed():  # 保持打开
                    page = await context.new_page()
                await page.goto(room_url)
                await page.evaluate(javascript)

            await asyncio.sleep(check_interval)
            await broadcast_message({"state": "alive", "interval": check_interval})  # 解决客户端同步读取模式下的挂起问题


# 运行hub
def run_hub_forever(listen_port, room_url, script):
    try:
        ws_future = websockets.serve(ws_handler, "localhost", listen_port)
        logger.info(f"Hub server listen at: {listen_port}")
        room_future = open_room(room_url, script)
        asyncio.gather(room_future, ws_future)
        asyncio.get_event_loop().run_forever()
    except Exception as ex:
        logger.error(f"Hub server exception: {ex}")


if __name__ == "__main__":
    room_douyin = "https://live.douyin.com/208754230598"  # douyin room url
    ws_port = 88  # websocket listen port
    
    run_hub_forever(ws_port, room_douyin, script_douyin)
