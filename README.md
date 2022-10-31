# 获取抖音弹幕 DouYin Danmu

## 思路
1. 通过playwright向浏览器（Edge）注入javascript，使用MutationObserver监听聊天栏弹幕变化，分析出弹幕内容
2. 以抖音为例，其他平台可简单修改javascript代码实现，通用但是比较笨拙。

# 依赖
- asyncio
- playwright，须同时安装对应浏览器驱动
- logging
