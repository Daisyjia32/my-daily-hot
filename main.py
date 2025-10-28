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
    """抓取新榜低粉爆文榜TOP10 - Cookie格式修复版"""
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
        
        print(f"原始Cookie长度: {len(newrank_cookie)}")
        print(f"Cookie内容预览: {newrank_cookie[:100]}...")
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # 修复Cookie解析 - 处理JavaScript控制台输出格式
            print("解析Cookie...")
            cookies = []
            
            # 方法1：按行分割，每行是一个Cookie
            lines = newrank_cookie.strip().split('\n')
            print(f"按行分割得到 {len(lines)} 行")
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                    
                # 跳过JavaScript输出标记（如 "VM208:5"）
                if re.match(r'^VM\d+:\d+', line):
                    print(f"跳过JavaScript标记行: {line}")
                    continue
                
                # 提取Cookie名和值
                if '=' in line:
                    # 找到第一个等号分割名称和值
                    equal_pos = line.find('=')
                    name = line[:equal_pos].strip()
                    value = line[equal_pos+1:].strip()
                    
                    # 清理值（移除可能的分号和其他字符）
                    if ';' in value:
                        value = value.split(';')[0]
                    
                    if name and value:
                        cookie_obj = {
                            'name': name,
                            'value': value,
                            'domain': '.newrank.cn',
                            'path': '/'
                        }
                        cookies.append(cookie_obj)
                        print(f"Cookie {len(cookies)}: {name}={value[:15]}...")
                else:
                    print(f"跳过无效行 {line_num}: {line}")
            
            print(f"成功解析 {len(cookies)} 个有效Cookie")
            
            if not cookies:
                print("❌ 没有解析出有效的Cookie")
                browser.close()
                return [{
                    'title': '⚠️ Cookie解析失败',
                    'url': 'https://www.newrank.cn/hotInfo?platform=GZH&rankType=3'
                }]
            
            # 添加Cookie到浏览器上下文
            try:
                context.add_cookies(cookies)
                print("✅ Cookie设置成功")
            except Exception as e:
                print(f"❌ Cookie设置失败: {e}")
                browser.close()
                return [{
                    'title': '⚠️ Cookie格式错误',
                    'url': 'https://www.newrank.cn/hotInfo?platform=GZH&rankType=3'
                }]
            
            # 访问目标页面
            print("访问低粉爆文榜页面...")
            page.goto('https://www.newrank.cn/hotInfo?platform=GZH&rankType=3', timeout=60000)
            
            # 等待加载
            page.wait_for_timeout(5000)
            
            # 检查登录状态
            page_title = page.title()
            page_text = page.inner_text('body')
            
            print(f"页面标题: {page_title}")
            print(f"页面包含'低粉爆文': {'低粉爆文' in page_text}")
            print(f"页面包含'登录': {'登录' in page_text}")
            
            if '低粉爆文' in page_text and '登录' not in page_text:
                print("✅ 登录成功！")
                
                # 简单查找文章
                all_links = page.query_selector_all('a')
                print(f"找到 {len(all_links)} 个链接")
                
                for i, link in enumerate(all_links[:30]):
                    if len(newrank_list) >= 10:
                        break
                        
                    text = link.inner_text().strip()
                    if len(text) > 8 and len(text) < 60:
                        href = link.get_attribute('href') or ''
                        if href and not href.startswith('http'):
                            full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                        else:
                            full_url = href
                        
                        newrank_list.append({
                            'title': text,
                            'url': full_url
                        })
                        print(f"文章 {len(newrank_list)}: {text}")
            else:
                print("❌ 登录状态异常")
                print(f"页面内容预览: {page_text[:300]}")
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
        if not newrank_list:
            return [{
                'title': '⚠️ 登录成功但未找到文章',
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
        text_content += "📚 知乎热榜 TOP 30\n"
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
