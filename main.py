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
    """抓取新榜低粉爆文榜TOP10 - 优化版本"""
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
        
        print("使用优化方法提取文章标题...")
        
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
            
            # 方法1：直接提取表格中的标题文本
            print("方法1：提取表格数据行...")
            
            # 查找表格行
            rows = page.query_selector_all('tr, .ant-table-row, [class*="row"]')
            print(f"找到 {len(rows)} 个数据行")
            
            seen_titles = set()
            count = 0
            
            for row in rows:
                if count >= 10:
                    break
                    
                try:
                    # 获取整行文本
                    row_text = row.inner_text().strip()
                    if not row_text:
                        continue
                    
                    # 分割成行
                    lines = [line.strip() for line in row_text.split('\n') if line.strip()]
                    
                    # 分析每行文本，识别标题
                    for line in lines:
                        # 标题特征：长度适中，包含标点符号，不包含元数据关键词
                        if (len(line) >= 10 and len(line) <= 80 and
                            any(char in line for char in ['：', '！', '？', '…', '，', '。', '"', '“', '”', '.']) and
                            not any(keyword in line for keyword in ['粉丝数', '发布于', '阅读数', '点赞数', '转发数', '收藏', '更多', '登录', '注册', '新榜', '头条', '原']) and
                            not re.match(r'^\d+$', line) and  # 不是纯数字
                            not re.match(r'^[0-9.,wW\+]+$', line) and  # 不是统计数字
                            not re.match(r'^[A-Za-z\s]+$', line)):  # 不是纯英文
                            
                            # 进一步验证：检查是否包含中文（大多数标题都有中文）
                            if any('\u4e00' <= char <= '\u9fff' for char in line):
                                # 清理标题：移除可能的省略号和多余空格
                                clean_title = re.sub(r'\s+', ' ', line)
                                clean_title = clean_title.split('...')[0].split('…')[0].strip()
                                
                                if (clean_title and 
                                    clean_title not in seen_titles and 
                                    len(clean_title) >= 10):
                                    
                                    seen_titles.add(clean_title)
                                    
                                    # 在行中查找链接
                                    link_elem = row.query_selector('a')
                                    href = link_elem.get_attribute('href') if link_elem else ''
                                    
                                    if href and not href.startswith('http'):
                                        full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                                    else:
                                        full_url = href if href else 'https://www.newrank.cn'
                                    
                                    newrank_list.append({
                                        'title': clean_title,
                                        'url': full_url
                                    })
                                    count += 1
                                    print(f"✅ 提取第{count}条: {clean_title}")
                                    break  # 每行只取一个标题
                                    
                except Exception as e:
                    continue
            
            # 方法2：如果方法1不够，使用更简单的文本分析
            if count < 10:
                print("方法2：使用页面文本分析...")
                
                # 获取整个页面的文本
                page_text = page.inner_text('body')
                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                
                for line in lines:
                    if count >= 10:
                        break
                        
                    # 更严格的标题识别
                    if (len(line) >= 15 and len(line) <= 70 and
                        any(char in line for char in ['：', '！', '？', '…', '，', '。']) and
                        not any(keyword in line for keyword in ['粉丝数', '发布于', '阅读数', '点赞数', '转发数', '收藏', '更多', '登录', '注册']) and
                        not re.match(r'^\d', line) and  # 不以数字开头
                        any('\u4e00' <= char <= '\u9fff' for char in line) and  # 包含中文
                        line not in seen_titles):
                        
                        clean_title = re.sub(r'\s+', ' ', line)
                        seen_titles.add(clean_title)
                        
                        newrank_list.append({
                            'title': clean_title,
                            'url': 'https://www.newrank.cn'
                        })
                        count += 1
                        print(f"✅ 文本分析第{count}条: {clean_title}")
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
        # 确保返回10条数据
        if len(newrank_list) > 10:
            newrank_list = newrank_list[:10]
        
        if not newrank_list:
            return [{
                'title': '⚠️ 无法识别页面结构',
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
