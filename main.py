import requests
import os
import json
from datetime import datetime
from urllib.parse import quote

FEISHU_WEBHOOK_URL = os.environ['FEISHU_WEBHOOK_URL']

def get_weibo_hot():
    """抓取微博热搜榜 - 修复版"""
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
            count = 0
            
            # 改进的过滤逻辑：只取有真实排名的热搜
            for item in data['data']['realtime']:
                # 关键过滤条件：必须有真实排名且不是广告
                if item.get('realpos') and item.get('realpos', 0) > 0 and item.get('flag') != 2:
                    # 修复链接：使用正确的微博搜索URL
                    search_word = quote(item['word'])
                    weibo_url = f"https://s.weibo.com/weibo?q={search_word}"
                    
                    hot_list.append({
                        'title': item['note'],
                        'url': weibo_url,
                        'rank': item['realpos']  # 添加排名信息用于排序
                    })
                    count += 1
                    if count >= 10:
                        break
            
            # 按真实排名排序
            hot_list.sort(key=lambda x: x['rank'])
            print(f"过滤后的微博热搜数量: {len(hot_list)}")
            return hot_list
        else:
            print(f"微博请求失败，状态码：{response.status_code}")
            return []
    except Exception as e:
        print(f"获取微博热搜出错: {e}")
        return []

def get_zhihu_hot():
    """抓取知乎热榜 - 使用备用方案"""
    try:
        # 方案1：尝试使用免认证的第三方接口
        url = "https://api.zhihu.com/topstory/hot-list?limit=10"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.zhihu.com/',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"知乎备用接口状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            hot_list = []
            for item in data['data']:
            target = item.get('target', {})
            title = target.get('title', '无标题')
            url = target.get('url', '')
    
    # 修复知乎链接 - 新版本
    if url and 'api.zhihu.com' in url:
        # 从API链接中提取问题ID，然后构建正确的知乎链接
        if '/questions/' in url:
            question_id = url.split('/questions/')[-1]
            url = f"https://www.zhihu.com/question/{question_id}"
        else:
            # 如果无法提取问题ID，使用备用方案
            url = "https://www.zhihu.com/hot"
    elif url and 'zhihu.com' not in url:
        # 原来的备用方案
        url = f"https://www.zhihu.com/question/{target.get('id', '')}"
    elif not url:
        # 如果没有链接，指向知乎热榜
        url = "https://www.zhihu.com/hot"
                
                hot_list.append({
                    'title': title,
                    'url': url
                })
            return hot_list
        else:
            print("知乎备用接口也失败了，尝试其他方案...")
            return get_zhihu_hot_fallback()
            
    except Exception as e:
        print(f"获取知乎热榜出错: {e}")
        return get_zhihu_hot_fallback()

def get_zhihu_hot_fallback():
    """知乎备用方案：返回提示信息"""
    return [{
        'title': '⚠️ 知乎热榜暂时无法获取（需要认证）',
        'url': 'https://www.zhihu.com/hot'
    }]

def send_to_feishu(weibo_data, zhihu_data):
    """发送消息到飞书 - 优化版"""
    # 构建更清晰的消息格式
    text_content = "🌐 每日热点速递\n\n"
    
    # 微博部分
    if weibo_data and len(weibo_data) > 0:
        text_content += "🔥 微博热搜 TOP 10\n"
        for i, item in enumerate(weibo_data, 1):
            text_content += f"{i}. {item['title']}\n   🔗 {item['url']}\n"
        text_content += "\n"
    else:
        text_content += "❌ 今日微博热搜获取失败\n\n"
    
    # 知乎部分
    if zhihu_data and len(zhihu_data) > 0:
        text_content += "📚 知乎热榜\n"
        for i, item in enumerate(zhihu_data, 1):
            text_content += f"{i}. {item['title']}\n"
            if 'zhihu.com' in item['url']:
                text_content += f"   🔗 {item['url']}\n"
        text_content += "\n"
    else:
        text_content += "❌ 今日知乎热榜获取失败\n"
    
    # 添加时间戳
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text_content += f"\n⏰ 更新时间: {current_time}"
    
    # 发送到飞书
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
