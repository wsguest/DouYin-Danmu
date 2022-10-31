import asyncio
import logging
from playwright.async_api import async_playwright

debug = True  # 调试状态

# 日志输出设置
logger = logging.getLogger("ws_hub")
logger.setLevel("DEBUG" if debug else "INFO")
fmt_str = "%(levelname)1.1s [%(asctime)s] %(message)s"
fmt = logging.Formatter(fmt=fmt_str, datefmt=None)
handler_console = logging.StreamHandler()
handler_console.setFormatter(fmt)
logger.addHandler(handler_console)


# 输出消息
async def print_message(msg: dict):
    logger.debug(msg)


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
        await context.expose_function(callback_name, print_message)
        page = await context.new_page()
        while True:
            if page.is_closed() or page.url != room_url:  # 保持打开
                if page.is_closed():  
                    page = await context.new_page()
                await page.goto(room_url)
                await page.evaluate(javascript)

            await asyncio.sleep(check_interval)


# 运行hub
def run_hub_forever(room_url, script):
    try:
        room_future = open_room(room_url, script)
        logger.info(f"Hub started.")
        asyncio.gather(room_future)
        asyncio.get_event_loop().run_forever()
    except Exception as ex:
        logger.error(f"Hub exception: {ex}")


if __name__ == "__main__":
    room_douyin = "https://live.douyin.com/208754230598"  # douyin room url
    run_hub_forever(room_douyin, script_douyin)
