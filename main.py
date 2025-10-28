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
    """抓取新榜低粉爆文榜TOP10 - 表格结构版"""
    try:
        from playwright.sync_api import sync_playwright
        import os
        
        print("开始抓取新榜低粉爆文榜...")
        newrank_list = []
        
        # 从环境变量获取Cookie
        newrank_cookie = os.environ.get('NEWRANK_COOKIE', '')
        
        if not newrank_cookie:
            return [{
                'title': '⚠️ 未设置新榜Cookie',
                'url': 'https://www.newrank.cn/hotInfo?platform=GZH&rankType=3'
            }]
        
        print("使用Playwright直接定位榜单表格...")
        
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
            
            # 策略：直接查找包含具体文章数据的区域
            print("查找包含具体文章数据的区域...")
            
            # 方法1：查找包含"陈道明"等具体文章标题的区域
            page_text = page.inner_text('body')
            if '陈道明' in page_text:
                print("✅ 页面包含目标文章数据")
            else:
                print("❌ 页面不包含目标文章数据")
            
            # 方法2：查找表格行或列表项，包含阅读数、粉丝数等指标
            print("查找包含指标数据的元素...")
            
            # 查找包含阅读数、粉丝数等指标的元素
            elements_with_metrics = []
            
            # 可能的指标关键词
            metrics_keywords = ['粉丝数', '阅读数', '点赞数', '转发数', '10W+', 'w+', '发布于']
            
            all_elements = page.query_selector_all('tr, div, li, article, section')
            for element in all_elements:
                try:
                    text = element.inner_text().strip()
                    # 检查是否包含指标关键词且有合理长度
                    if (len(text) > 50 and len(text) < 1000 and
                        any(keyword in text for keyword in metrics_keywords)):
                        elements_with_metrics.append({
                            'element': element,
                            'text': text
                        })
                except:
                    continue
            
            print(f"找到 {len(elements_with_metrics)} 个包含指标的元素")
            
            # 显示前5个用于调试
            for i, item in enumerate(elements_with_metrics[:5]):
                print(f"指标元素 {i+1}: {item['text'][:100]}...")
            
            # 从这些元素中提取文章标题
            count = 0
            for item in elements_with_metrics:
                if count >= 10:
                    break
                
                text = item['text']
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                # 查找文章标题（通常是包含标点符号的较长行）
                title = ""
                for line in lines:
                    # 标题特征：包含中文标点，长度适中，不包含指标关键词
                    if (len(line) > 10 and len(line) < 100 and
                        any(char in line for char in ['：', '！', '，', '。', '？', '"', '“', '”']) and
                        not any(keyword in line for keyword in ['粉丝数', '发布于', '阅读数', '点赞数', '转发数', '收藏', '更多'])):
                        title = line
                        break
                
                # 如果没找到，尝试第一行
                if not title and lines:
                    title = lines[0]
                
                if title and len(title) > 5:
                    # 查找链接
                    element = item['element']
                    link_elem = element.query_selector('a')
                    href = link_elem.get_attribute('href') if link_elem else ''
                    
                    # 构建完整URL
                    if href and not href.startswith('http'):
                        full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                    else:
                        full_url = href if href else 'https://www.newrank.cn'
                    
                    newrank_list.append({
                        'title': title,
                        'url': full_url
                    })
                    count += 1
                    print(f"✅ 文章第{count}条: {title}")
            
            # 方法3：如果还没找到，使用更精确的选择器
            if not newrank_list:
                print("使用精确选择器方案...")
                
                # 尝试各种可能的选择器组合
                selectors_to_try = [
                    'tr',  # 表格行
                    '.ant-table-row',  # Ant Design 表格
                    '.el-table__row',  # Element UI 表格
                    '[class*="row"]',
                    '[class*="item"]',
                    '[class*="article"]',
                    '[class*="content"]'
                ]
                
                for selector in selectors_to_try:
                    elements = page.query_selector_all(selector)
                    print(f"选择器 '{selector}' 找到 {len(elements)} 个元素")
                    
                    for element in elements:
                        if count >= 10:
                            break
                        
                        text = element.inner_text().strip()
                        if len(text) > 50 and any(keyword in text for keyword in metrics_keywords):
                            # 提取标题
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            for line in lines:
                                if (len(line) > 10 and len(line) < 100 and
                                    any(char in line for char in ['：', '！', '，', '。', '？'])):
                                    
                                    link_elem = element.query_selector('a')
                                    href = link_elem.get_attribute('href') if link_elem else ''
                                    
                                    if href and not href.startswith('http'):
                                        full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                                    else:
                                        full_url = href if href else 'https://www.newrank.cn'
                                    
                                    newrank_list.append({
                                        'title': line,
                                        'url': full_url
                                    })
                                    count += 1
                                    print(f"✅ 精确选择器第{count}条: {line}")
                                    break
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
        if not newrank_list:
            return [{
                'title': '⚠️ 无法定位榜单表格结构',
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
