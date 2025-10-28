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
    """抓取新榜低粉爆文榜TOP10 - 修复版"""
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
            
            # 等待页面加载
            print("等待页面加载...")
            page.wait_for_timeout(8000)
            
            # 更精准的选择器策略
            print("尝试精准选择器...")
            
            # 方案1：尝试直接定位文章列表容器
            article_container_selectors = [
                '.rank-list',
                '.list-container',
                '.hot-list',
                '.content-list',
                '.weui-panel',
                '[class*="rank"]',
                '[class*="list"]'
            ]
            
            articles = []
            for container_selector in article_container_selectors:
                container = page.query_selector(container_selector)
                if container:
                    print(f"找到容器: {container_selector}")
                    # 在容器内查找文章项
                    items = container.query_selector_all('[class*="item"], [class*="article"], [class*="media"]')
                    if items:
                        articles = items
                        break
            
            # 方案2：如果没找到容器，直接搜索包含特定文本的元素
            if not articles:
                print("尝试搜索包含公众号名的元素...")
                # 查找可能包含公众号名称或文章标题的元素
                potential_elements = page.query_selector_all('[class*="name"], [class*="title"], [class*="account"]')
                articles = [elem for elem in potential_elements if len(elem.inner_text().strip()) > 2]
            
            # 方案3：最后的手段 - 查找所有包含链接且有较长文本的元素
            if not articles:
                print("使用最终方案：查找所有链接...")
                all_links = page.query_selector_all('a')
                articles = []
                for link in all_links:
                    text = link.inner_text().strip()
                    href = link.get_attribute('href') or ''
                    # 只保留有较长文本且可能是文章链接的元素
                    if len(text) > 4 and ('article' in href or 'detail' in href or '/p/' in href):
                        articles.append(link)
            
            print(f"最终找到 {len(articles)} 个候选元素")
            
            # 提取前10个有效元素的数据
            count = 0
            for i, article in enumerate(articles):
                if count >= 10:
                    break
                    
                try:
                    text_content = article.inner_text().strip()
                    
                    # 过滤条件：文本长度合适，且不包含明显不是文章标题的文本
                    if (len(text_content) < 5 or len(text_content) > 100 or 
                        any(keyword in text_content for keyword in ['登录', '注册', '首页', '热门', '搜索', '下载'])):
                        continue
                    
                    # 获取链接
                    href = article.get_attribute('href') or ''
                    
                    # 构建完整链接
                    if href and not href.startswith('http'):
                        full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                    else:
                        full_url = href if href else 'https://www.newrank.cn'
                    
                    newrank_list.append({
                        'title': text_content,
                        'url': full_url
                    })
                    
                    print(f"新榜第{count+1}条: {text_content[:30]}...")
                    count += 1
                    
                except Exception as e:
                    print(f"解析元素 {i} 出错: {e}")
                    continue
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
        # 如果没有找到有效数据，返回提示
        if not newrank_list:
            return [{
                'title': '⚠️ 找到元素但无法解析内容，可能需要人工查看页面结构',
                'url': 'https://www.newrank.cn/hotInfo?platform=GZH&rankType=3'
            }]
        
        return newrank_list
        
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
