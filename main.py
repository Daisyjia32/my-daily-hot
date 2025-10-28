import requests
import os
import json
from datetime import datetime

FEISHU_WEBHOOK_URL = os.environ['FEISHU_WEBHOOK_URL']

def get_weibo_hot():
    """抓取微博热搜榜"""
    try:
        url = "https://weibo.com/ajax/side/hotSearch"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://weibo.com/',
        }
        response = requests.get(url, headers=headers, timeout=10)
        print(f"微博接口状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.zhihu.com/hot',
        }
        response = requests.get(url, headers=headers, timeout=10)
        print(f"知乎接口状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            hot_list = []
            for item in data['data'][:10]:
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
            return []
    except Exception as e:
        print(f"获取知乎热榜出错: {e}")
        return []

def send_to_feishu(weibo_data, zhihu_data):
    """发送消息到飞书 - 修复版"""
    # 构建纯文本消息
    text_content = "🌐 每日热点速递\n\n"
    
    # 添加微博热点
    if weibo_data:
        text_content += "🔥 微博热搜 TOP 10\n"
        for i, item in enumerate(weibo_data, 1):
            text_content += f"{i}. {item['title']}\n   {item['url']}\n"
        text_content += "\n"
    else:
        text_content += "❌ 今日微博热搜获取失败\n\n"
    
    # 添加知乎热点
    if zhihu_data:
        text_content += "📚 知乎热榜 TOP 10\n"
        for i, item in enumerate(zhihu_data, 1):
            text_content += f"{i}. {item['title']}\n   {item['url']}\n"
    else:
        text_content += "❌ 今日知乎热榜获取失败\n"
    
    # 使用最简单的text格式
    data = {
        "msg_type": "text",
        "content": {
            "text": text_content
        }
    }
    
    try:
        response = requests.post(FEISHU_WEBHOOK_URL, json=data, timeout=10)
        print(f"飞书推送结果: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"飞书推送失败: {e}")
        return False

def main():
    print("开始获取今日热点...")
    
    weibo_data = get_weibo_hot()
    zhihu_data = get_zhihu_hot()
    
    # 发送到飞书
    success = send_to_feishu(weibo_data, zhihu_data)
    
    if success:
        print("热点推送完成！")
    else:
        print("热点推送失败！")

if __name__ == '__main__':
    main()
