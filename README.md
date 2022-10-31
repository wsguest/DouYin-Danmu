# 抖音弹幕 DouYin-Danmu
##思路方法
1. 通过playwright向浏览器注入javascript，使用MutationObserver监听聊天栏弹幕变化，分析出弹幕内容
2. 使用websocket提供对外接口，其他应用连接websocket获取或发送内容
*以抖音为例，其他平台可简单修改实现，非常通用，缺点是比较笨拙*

# 依赖
- asyncio
- playwright
- websockets
