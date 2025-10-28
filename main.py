import requests
import os
import json
from datetime import datetime

FEISHU_WEBHOOK_URL = os.environ['FEISHU_WEBHOOK_URL']

def get_weibo_hot():
    """抓取微博热搜榜"""
    try:
        url = "https://weibo.com/ajax/side/hotSearch"
        # 新增：模拟真实浏览器的请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://weibo.com/',
            'Cookie': 'SUB=_2AkMSpYNSf8NxqwFRmP8Wy2PiaoVyywDEieKlH1YVJRMxHRl-yT9jqhS_ftRB6OcQKvY3UfTCsLtc-7V3SdfC1vY7mskS' # 这是一个示例Cookie，可能已过期，但有时不需要也能工作
        }
        response = requests.get(url, headers=headers, timeout=10)
        print(f"微博接口状态码: {response.status_code}") # 新增打印状态码
        if response.status_code == 200:
            data = response.json()
            print(f"微博返回的原始数据: {json.dumps(data, ensure_ascii=False)[:1000]}")
            hot_list = []
            for item in data['data']['realtime'][:10]:
                hot_list.append({
                    'title': item['note'],
                    'url': f"https://s.weibo.com/weibo?q=%23{item['word']}%23"
                })
            print(f"解析后的微博热点列表: {hot_list}")
            return hot_list
        else:
            print(f"微博请求失败，状态码：{response.status_code}")
            # 新增：打印失败返回的内容，便于调试
            print(f"微博返回内容: {response.text[:500]}") 
            return []
    except Exception as e:
        print(f"获取微博热搜出错: {e}")
        return []

def get_zhihu_hot():
    """抓取知乎热榜"""
    try:
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=10"
        # 增强的请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.zhihu.com/hot',
            # 知乎不需要Cookie也可以访问热榜
        }
        response = requests.get(url, headers=headers, timeout=10)
        print(f"知乎接口状态码: {response.status_code}") # 新增打印状态码
        if response.status_code == 200:
            data = response.json()
            hot_list = []
            for item in data['data'][:10]:
                # 增强解析逻辑，防止结构变化导致错误
                target = item.get('target', {})
                title = target.get('title', '无标题')
                url = target.get('url', '').replace("api.zhihu.com", "www.zhihu.com").replace("questions", "question")
                
                hot_list.append({
                    'title': title,
                    'url': url
                })
            return hot_list
        else:
            print(f"知乎请求失败，状态码：{response.status_code}")
            print(f"知乎返回内容: {response.text[:500]}")
            return []
    except Exception as e:
        print(f"获取知乎热榜出错: {e}")
        return []

def send_to_feishu(message):
    """发送消息到飞书"""
    data = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "🌐 每日热点速递",
                    "content": message
                }
            }
        }
    }
    try:
        response = requests.post(FEISHU_WEBHOOK_URL, json=data, timeout=10)
        print(f"飞书推送结果: {response.status_code}")
        # 新增：打印飞书返回
        print(f"飞书返回: {response.text}")
    except Exception as e:
        print(f"飞书推送失败: {e}")

def main():
    print("开始获取今日热点...")
    
    weibo_data = get_weibo_hot()
    zhihu_data = get_zhihu_hot()
    
    message_content = []
    
    if weibo_data:
        weibo_section = [
            [{"tag": "text", "text": "🔥 微博热搜 TOP 10\n", "style": {"bold": True}}]
        ]
        for i, item in enumerate(weibo_data, 1):
            weibo_section.append([
                {"tag": "text", "text": f"{i}. "},
                {"tag": "a", "text": item['title'], "href": item['url']}
            ])
        message_content.extend(weibo_section)
        message_content.append([])
    else:
        # 新增：如果微博失败，添加提示
        message_content.append([{"tag": "text", "text": "❌ 今日微博热搜获取失败\n"}])
        message_content.append([])
    
    if zhihu_data:
        zhihu_section = [
            [{"tag": "text", "text": "📚 知乎热榜 TOP 10\n", "style": {"bold": True}}]
        ]
        for i, item in enumerate(zhihu_data, 1):
            zhihu_section.append([
                {"tag": "text", "text": f"{i}. "},
                {"tag": "a", "text": item['title'], "href": item['url']}
            ])
        message_content.extend(zhihu_section)
    else:
        # 新增：如果知乎失败，添加提示
        message_content.append([{"tag": "text", "text": "❌ 今日知乎热榜获取失败\n"}])
    
    # 修改：即使部分失败也发送推送，让您知道情况
    send_to_feishu(message_content)
    print("热点推送完成！")

if __name__ == '__main__':
    main()
