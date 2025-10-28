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
    """抓取新榜低粉爆文榜TOP10 - 精准抓取文章标题版"""
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
        
        print("使用Playwright访问并抓取具体文章标题...")
        
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
            
            # 直接访问已经筛选好的页面
            print("访问已筛选的低粉爆文榜页面...")
            page.goto('https://www.newrank.cn/hotInfo?platform=GZH&rankType=3', timeout=60000)
            
            # 等待页面加载
            print("等待榜单数据加载...")
            page.wait_for_timeout(8000)
            
            # 检查页面内容
            page_text = page.inner_text('body')
            print(f"页面内容长度: {len(page_text)}")
            
            # 保存截图用于调试
            page.screenshot(path='newrank_final.png')
            print("已保存页面截图: newrank_final.png")
            
            # 策略：直接查找符合文章标题特征的所有文本
            print("查找所有可能的文章标题...")
            
            # 获取页面所有文本节点
            all_text_elements = page.query_selector_all('*')
            print(f"页面共有 {len(all_text_elements)} 个元素")
            
            # 收集所有可能的标题文本
            potential_titles = []
            
            for element in all_text_elements:
                try:
                    text = element.inner_text().strip()
                    
                    # 精准匹配文章标题特征（基于您提供的例子）
                    is_article_title = (
                        len(text) >= 10 and len(text) <= 100 and  # 合理长度范围
                        re.search(r'[。！？…]', text) and  # 包含中文标点（完整句子）
                        not any(keyword in text for keyword in [  # 排除非文章文本
                            '登录', '注册', '首页', '新榜', '报告', '白皮书', 
                            '热门', '榜单', '小工具', '品牌声量', '新红', '新抖',
                            '新快', '新视', '新站', '开发者', '搜热度', '阅读', 
                            '点赞', '转发', '收藏', '更多', '粉丝数', '发布时间'
                        ]) and
                        not text.startswith('http') and  # 排除URL
                        not text.isdigit() and  # 排除纯数字
                        ' ' not in text or len(text.split()) > 2  # 应该是连续文本或包含多个词
                    )
                    
                    if is_article_title:
                        # 进一步清理文本
                        clean_text = re.sub(r'\s+', ' ', text)  # 合并多余空格
                        clean_text = clean_text.split('...')[0]  # 移除省略号后的内容
                        clean_text = clean_text.split('扫码')[0]  # 移除扫码提示
                        
                        if len(clean_text) > 8:
                            potential_titles.append(clean_text)
                            
                except:
                    continue
            
            print(f"找到 {len(potential_titles)} 个可能的文章标题")
            
            # 去重并显示前20个用于调试
            unique_titles = []
            seen = set()
            for title in potential_titles:
                # 使用前20个字符去重
                key = title[:20]
                if key not in seen:
                    seen.add(key)
                    unique_titles.append(title)
            
            print("=== 找到的标题样本 ===")
            for i, title in enumerate(unique_titles[:20]):
                print(f"{i+1}. {title}")
            print("===================")
            
            # 提取前10个作为结果
            count = 0
            for title in unique_titles:
                if count >= 10:
                    break
                
                # 最终验证：确保是真正的文章标题（基于您提供的例子特征）
                if (len(title) > 8 and 
                    any(char in title for char in ['：', '！', '，', '。', '？']) and  # 包含中文标点
                    not any(keyword in title for keyword in ['新榜', '首页', '登录'])):
                    
                    # 查找这个标题对应的链接
                    title_element = page.query_selector(f'text="{title}"')
                    href = ""
                    
                    if title_element:
                        # 找到包含这个标题的链接元素
                        link_element = title_element.evaluate_handle('(elem) => elem.closest("a")')
                        if link_element:
                            href = link_element.get_attribute('href') or ''
                    
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
                    print(f"✅ 确认文章第{count}条: {title}")
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
        if not newrank_list:
            return [{
                'title': '⚠️ 找到标题但无法确认链接',
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
