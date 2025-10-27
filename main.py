import requests
import os
import json
from datetime import datetime

# 从GitHub仓库的"Secrets"中获取飞书机器人Webhook地址
FEISHU_WEBHOOK_URL = os.environ['FEISHU_WEBHOOK_URL']

def get_weibo_hot():
    """抓取微博热搜榜"""
    try:
        url = "https://weibo.com/ajax/side/hotSearch"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # 解析数据结构，提取前十名
            hot_list = []
            for item in data['data']['realtime'][:10]:
                hot_list.append({
                    'title': item['note'],
                    'url': f"https://s.weibo.com/weibo?q=%23{item['word']}%23"
                })
            return hot_list
        else:
            print(f"微博请求失败，状态码：{response.status_code}")
            return []
    except Exception as e:
        print(f"获取微博热搜出错: {e}")
        return []

def get_zhihu_hot():
    """抓取知乎热榜"""
    try:
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=10"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            hot_list = []
            for item in data['data'][:10]:
                hot_list.append({
                    'title': item['target']['title'],
                    'url': item['target']['url'].replace("api.zhihu.com", "www.zhihu.com").replace("questions", "question")
                })
            return hot_list
        else:
            print(f"知乎请求失败，状态码：{response.status_code}")
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
    except Exception as e:
        print(f"飞书推送失败: {e}")

def main():
    print("开始获取今日热点...")
    
    # 获取各平台数据
    weibo_data = get_weibo_hot()
    zhihu_data = get_zhihu_hot()
    
    # 构建飞书消息内容
    message_content = []
    
    # 微博部分
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
        message_content.append([])  # 空行分隔
    
    # 知乎部分
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
    
    # 发送到飞书
    if message_content:
        send_to_feishu(message_content)
        print("热点推送完成！")
    else:
        print("未获取到任何数据，推送取消。")

if __name__ == '__main__':
    main()
