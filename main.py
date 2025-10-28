import requests
import os
import json
from datetime import datetime
from urllib.parse import quote

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
            count = 0
            
            for item in data['data']['realtime']:
                if item.get('realpos') and item.get('realpos', 0) > 0 and item.get('flag') != 2:
                    search_word = quote(item['word'])
                    weibo_url = f"https://s.weibo.com/weibo?q={search_word}"
                    
                    hot_list.append({
                        'title': item['note'],
                        'url': weibo_url,
                        'rank': item['realpos']
                    })
                    count += 1
                    if count >= 10:
                        break
            
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
    """抓取知乎热榜"""
    try:
        url = "https://api.zhihu.com/topstory/hot-list?limit=10"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.zhihu.com/',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"知乎接口状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            hot_list = []
            for item in data['data']:
                target = item.get('target', {})
                title = target.get('title', '无标题')
                url = target.get('url', '')
                
                # 修复知乎链接
                if url and 'api.zhihu.com' in url:
                    if '/questions/' in url:
                        question_id = url.split('/questions/')[-1]
                        url = f"https://www.zhihu.com/question/{question_id}"
                    else:
                        url = "https://www.zhihu.com/hot"
                elif url and 'zhihu.com' not in url:
                    url = f"https://www.zhihu.com/question/{target.get('id', '')}"
                elif not url:
                    url = "https://www.zhihu.com/hot"
                
                hot_list.append({
                    'title': title,
                    'url': url
                })
            return hot_list
        else:
            print("知乎接口失败，返回提示信息")
            return [{
                'title': '⚠️ 知乎热榜暂时无法获取',
                'url': 'https://www.zhihu.com/hot'
            }]
            
    except Exception as e:
        print(f"获取知乎热榜出错: {e}")
        return [{
            'title': '⚠️ 知乎热榜获取出错',
            'url': 'https://www.zhihu.com/hot'
        }]

def get_newrank_low_fans():
    """抓取新榜低粉爆文榜TOP10 - 调试版"""
    try:
        from playwright.sync_api import sync_playwright
        
        print("开始抓取新榜低粉爆文榜...")
        newrank_list = []
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 访问新榜页面
            print("正在访问新榜页面...")
            page.goto('https://www.newrank.cn/hotInfo?platform=GZH&rankType=3', timeout=60000)
            
            # 等待更长时间确保页面加载完成
            print("等待页面加载...")
            page.wait_for_timeout(8000)
            
            # 先截图保存页面状态用于调试
            page.screenshot(path='newrank_page.png')
            print("已保存页面截图")
            
            # 获取页面HTML内容用于分析
            html_content = page.content()
            print(f"页面标题: {page.title()}")
            
            # 尝试多种可能的选择器
            selectors_to_try = [
                '.list-item',
                '.rank-item',
                '.item',
                '.list-group-item',
                '[class*="list"]',
                '[class*="item"]',
                '.weui-media-box'
            ]
            
            found_articles = []
            for selector in selectors_to_try:
                articles = page.query_selector_all(selector)
                if articles and len(articles) > 5:  # 如果找到足够多的元素
                    print(f"使用选择器 '{selector}' 找到了 {len(articles)} 个元素")
                    found_articles = articles
                    break
                else:
                    print(f"选择器 '{selector}' 找到 {len(articles) if articles else 0} 个元素")
            
            # 如果没找到，尝试通过文本内容查找
            if not found_articles:
                print("尝试通过文本内容查找...")
                page_content = page.inner_text('body')
                if '低粉爆文' in page_content:
                    print("页面包含'低粉爆文'文本")
                else:
                    print("页面不包含'低粉爆文'文本")
                
                # 查找所有链接
                all_links = page.query_selector_all('a')
                print(f"页面中共有 {len(all_links)} 个链接")
                
                # 取前20个链接作为备选
                found_articles = all_links[:20]
            
            # 提取数据
            for i, article in enumerate(found_articles[:10]):
                try:
                    # 获取元素的文本内容
                    text_content = article.inner_text().strip()
                    if not text_content or len(text_content) < 5:
                        continue
                    
                    # 获取链接
                    href = article.get_attribute('href') or ''
                    
                    # 构建完整链接
                    if href and not href.startswith('http'):
                        full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                    else:
                        full_url = href if href else 'https://www.newrank.cn'
                    
                    newrank_list.append({
                        'title': text_content[:100],  # 限制标题长度
                        'url': full_url
                    })
                    
                    print(f"新榜第{i+1}条: {text_content[:50]}...")
                    
                except Exception as e:
                    print(f"解析新榜第{i+1}条出错: {e}")
                    continue
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        return newrank_list if newrank_list else [{
            'title': '⚠️ 新榜低粉爆文榜数据解析失败，需要调整选择器',
            'url': 'https://www.newrank.cn/hotInfo?platform=GZH&rankType=3'
        }]
        
    except Exception as e:
        print(f"获取新榜低粉爆文榜出错: {e}")
        return [{
            'title': '⚠️ 新榜低粉爆文榜获取失败',
            'url': 'https://www.newrank.cn/hotInfo?platform=GZH&rankType=3'
        }]

def send_to_feishu(weibo_data, zhihu_data, newrank_data):
    """发送消息到飞书"""
    text_content = "🌐 每日热点速递\n\n"
    
    # 微博部分
    if weibo_data and len(weibo_data) > 0:
        text_content += "🔥 微博热搜 TOP 10\n"
        for i, item in enumerate(weibo_data, 1):
            text_content += f"{i}. {item['title']}\n   🔗 {item['url']}\n"
        text_content += "\n"
    
    # 知乎部分
    if zhihu_data and len(zhihu_data) > 0:
        text_content += "📚 知乎热榜 TOP 10\n"
        for i, item in enumerate(zhihu_data, 1):
            text_content += f"{i}. {item['title']}\n"
            if 'zhihu.com' in item['url']:
                text_content += f"   🔗 {item['url']}\n"
        text_content += "\n"
    
    # 新榜低粉爆文榜部分
    if newrank_data and len(newrank_data) > 0:
        text_content += "💥 新榜低粉爆文榜 TOP 10\n"
        for i, item in enumerate(newrank_data, 1):
            text_content += f"{i}. {item['title']}\n"
            if 'newrank.cn' in item['url']:
                text_content += f"   🔗 {item['url']}\n"
        text_content += "\n"
    
    # 添加时间戳
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text_content += f"⏰ 更新时间: {current_time}"
    
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
    newrank_data = get_newrank_low_fans()
    
    # 发送到飞书
    success = send_to_feishu(weibo_data, zhihu_data, newrank_data)
    
    if success:
        print("热点推送完成！")
    else:
        print("热点推送失败！")

if __name__ == '__main__':
    main()
