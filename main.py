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
    """抓取新榜低粉爆文榜TOP10 - 精准提取文章链接版"""
    try:
        from playwright.sync_api import sync_playwright
        import os
        import re
        
        print("开始抓取新榜低粉爆文榜...")
        newrank_list = []
        
        # 从环境变量获取Cookie
        newrank_cookie = os.environ.get('NEWRANK_COOKIE', '')
        
        if not newrank_cookie:
            return [{
                'title': '⚠️ 未设置新榜Cookie',
                'url': 'https://www.newrank.cn/hotInfo?platform=GZH&rankType=3'
            }]
        
        print("使用Playwright精准提取文章链接...")
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # 设置Cookie
            print("设置登录Cookie...")
            cookies = []
            cookie_pairs = newrank_cookie.split(';')
            
            for cookie_str in cookie_pairs:
                cookie_str = cookie_str.strip()
                if '=' in cookie_str:
                    name, value = cookie_str.split('=', 1)
                    cookies.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.newrank.cn',
                        'path': '/'
                    })
            
            # 先访问首页设置Cookie
            page.goto('https://www.newrank.cn/', timeout=30000)
            context.add_cookies(cookies)
            
            # 访问目标页面
            print("访问低粉爆文榜页面...")
            page.goto('https://www.newrank.cn/hotInfo?platform=GZH&rankType=3', timeout=60000)
            
            # 等待页面加载
            print("等待榜单数据加载...")
            page.wait_for_timeout(8000)
            
            # 策略：专门查找指向微信文章的真实链接
            print("查找所有指向微信文章的链接...")
            
            # 获取页面所有链接
            all_links = page.query_selector_all('a')
            print(f"页面共有 {len(all_links)} 个链接")
            
            # 分析链接类型
            wechat_links = []
            other_links = []
            
            for link in all_links:
                href = link.get_attribute('href') or ''
                text = link.inner_text().strip()
                
                # 分类链接
                if 'mp.weixin.qq.com' in href:
                    wechat_links.append({
                        'text': text,
                        'href': href,
                        'element': link
                    })
                elif href:
                    other_links.append({
                        'text': text,
                        'href': href,
                        'element': link
                    })
            
            print(f"找到 {len(wechat_links)} 个微信文章链接")
            print(f"找到 {len(other_links)} 个其他链接")
            
            # 显示微信链接用于调试
            for i, link in enumerate(wechat_links[:5]):
                print(f"微信链接 {i+1}: {link['text'][:30]}... -> {link['href'][:50]}...")
            
            # 方法1：直接使用微信文章链接
            count = 0
            seen_titles = set()
            
            for link_info in wechat_links:
                if count >= 10:
                    break
                
                text = link_info['text'].strip()
                href = link_info['href']
                
                # 过滤条件：文本像文章标题
                if (len(text) > 10 and len(text) < 80 and
                    any(char in text for char in ['：', '！', '，', '。', '？', '"', '“', '”']) and
                    not any(keyword in text for keyword in ['登录', '注册', '首页', '新榜', '轻松', '账号', '找号', '社媒']) and
                    text not in seen_titles):
                    
                    seen_titles.add(text)
                    newrank_list.append({
                        'title': text,
                        'url': href  # 直接使用微信文章链接
                    })
                    count += 1
                    print(f"✅ 微信链接第{count}条: {text}")
            
            # 方法2：如果微信链接不够，从其他链接中提取文章标题
            if count < 10:
                print("从其他链接中补充文章标题...")
                
                for link_info in other_links:
                    if count >= 10:
                        break
                    
                    text = link_info['text'].strip()
                    href = link_info['href']
                    
                    # 更严格的过滤条件
                    is_article_title = (
                        len(text) > 15 and len(text) < 100 and
                        any(char in text for char in ['：', '！', '，', '。', '？', '…']) and  # 包含中文标点
                        not any(keyword in text for keyword in [  # 排除广告和导航
                            '登录', '注册', '首页', '新榜', '轻松', '账号', '找号', '社媒',
                            '营销', '推广', '投放', '创作', '数据', '回采', '作品'
                        ]) and
                        not text.startswith('http') and  # 排除URL文本
                        text not in seen_titles
                    )
                    
                    if is_article_title:
                        seen_titles.add(text)
                        
                        # 构建完整URL
                        if href and not href.startswith('http'):
                            full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                        else:
                            full_url = href
                        
                        newrank_list.append({
                            'title': text,
                            'url': full_url
                        })
                        count += 1
                        print(f"✅ 其他链接第{count}条: {text}")
            
            # 方法3：如果还是不够，使用更精确的文本匹配
            if count < 10:
                print("使用精确文本匹配...")
                
                # 查找包含具体文章标题的文本节点
                all_elements = page.query_selector_all('*')
                article_texts = []
                
                for element in all_elements:
                    try:
                        text = element.inner_text().strip()
                        # 匹配文章标题特征
                        if (len(text) > 20 and len(text) < 200 and
                            any(char in text for char in ['：', '！', '，', '。', '？', '…']) and
                            not any(keyword in text for keyword in ['登录', '注册', '首页']) and
                            text not in seen_titles):
                            
                            # 提取标题部分（第一行或主要部分）
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            if lines:
                                title_candidate = lines[0]
                                if len(title_candidate) > 10:
                                    article_texts.append({
                                        'text': title_candidate,
                                        'element': element
                                    })
                    except:
                        continue
                
                # 去重
                unique_articles = []
                seen_texts = set()
                for article in article_texts:
                    text_key = article['text'][:30]  # 前30字符去重
                    if text_key not in seen_texts:
                        seen_texts.add(text_key)
                        unique_articles.append(article)
                
                print(f"找到 {len(unique_articles)} 个可能的文章标题")
                
                for article in unique_articles:
                    if count >= 10:
                        break
                    
                    title = article['text']
                    element = article['element']
                    
                    # 查找链接
                    link_elem = element.query_selector('a')
                    href = link_elem.get_attribute('href') if link_elem else ''
                    
                    # 如果是微信文章链接，直接使用
                    if 'mp.weixin.qq.com' in href:
                        full_url = href
                    elif href and not href.startswith('http'):
                        full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                    else:
                        full_url = href if href else 'https://www.newrank.cn'
                    
                    if title not in seen_titles:
                        seen_titles.add(title)
                        newrank_list.append({
                            'title': title,
                            'url': full_url
                        })
                        count += 1
                        print(f"✅ 文本匹配第{count}条: {title}")
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
        if not newrank_list:
            return [{
                'title': '⚠️ 无法提取有效文章数据',
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
        text_content += "【🔥 微博热搜 TOP 10】\n"
        for i, item in enumerate(weibo_data, 1):
            text_content += f"{i}. {item['title']}\n   🔗 {item['url']}\n"
        text_content += "\n"
    
    # 知乎部分
    if zhihu_data and len(zhihu_data) > 0:
        text_content += "【📚 知乎热榜 TOP 30】\n"
        for i, item in enumerate(zhihu_data, 1):
            text_content += f"{i}. {item['title']}\n"
            if 'zhihu.com' in item['url']:
                text_content += f"   🔗 {item['url']}\n"
        text_content += "\n"
    
    # 新榜低粉爆文榜部分
    if newrank_data and len(newrank_data) > 0:
        text_content += "【💥 新榜低粉爆文榜 TOP 10】\n"
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
