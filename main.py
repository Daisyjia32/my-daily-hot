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
    """抓取新榜低粉爆文榜TOP10 - 最终链接优化版"""
    try:
        from playwright.sync_api import sync_playwright
        import os
        import re
        import time
        import urllib.parse
        
        def _is_valid_title(line, re_module):
            """判断一行文本是否是有效的文章标题"""
            # 基本长度检查
            if len(line) < 6 or len(line) > 120:
                return False
            
            # 必须包含中文
            if not any('\u4e00' <= char <= '\u9fff' for char in line):
                return False
            
            # 排除明显的非标题内容
            exclude_patterns = [
                r'^粉丝数', r'^发布于', r'^阅读数', r'^点赞数', r'^转发数',
                r'^收藏', r'^更多', r'^登录', r'^注册', r'^新榜',
                r'^头条', r'^原', r'^情感', r'^文摘', r'^科技', r'^美食',
                r'^乐活', r'^职场',
                r'^\d+$', r'^[0-9.,wW\+]+$', r'^http', r'^©', r'^首页'
            ]
            
            for pattern in exclude_patterns:
                if re_module.match(pattern, line):
                    return False
            
            # 排除包含作者特征的行
            author_indicators = ['粉丝数', '发布于', '深蓝画画', '故園柴扉', '茉怡说', '老田电脑', '胡言叨语', '催收圈', '阅享之', '爱穿裙子的长桑']
            if any(indicator in line for indicator in author_indicators):
                return False
            
            # 标题通常包含标点符号
            has_punctuation = any(char in line for char in ['：', '！', '？', '…', '，', '。', '"', '“', '”', '.', '|', '『', '』', '《', '》', '——', '与'])
            
            # 标题通常不包含统计数字模式
            has_stats = bool(re_module.search(r'\d+[万wW]', line)) or bool(re_module.search(r'\d+\.\d+[万wW]?', line))
            
            # 宽松条件
            return (has_punctuation or len(line) > 8) and not has_stats
        
        def _extract_wechat_url_from_captcha(captcha_url):
            """从验证链接中提取真实的微信文章链接"""
            try:
                print(f"解析验证链接: {captcha_url}")
                parsed_url = urllib.parse.urlparse(captcha_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                if 'target_url' in query_params:
                    target_url = query_params['target_url'][0]
                    # URL解码
                    real_url = urllib.parse.unquote(target_url)
                    print(f"✅ 提取到真实链接: {real_url}")
                    return real_url
                return captcha_url
            except Exception as e:
                print(f"解析验证链接失败: {e}")
                return captcha_url
        
        def _get_article_url(row, page):
            """从行中提取真实的文章链接"""
            try:
                print("开始提取文章链接...")
                
                # 方法1：直接查找包含文章数据的属性
                # 新榜通常在tr或td上存储文章数据
                article_data = row.get_attribute('data-url') or row.get_attribute('data-link')
                if article_data:
                    print(f"✅ 从data属性找到链接: {article_data}")
                    if 'mp.weixin.qq.com' in article_data:
                        return _extract_wechat_url_from_captcha(article_data)
                    return article_data
                
                # 方法2：查找所有可能的链接
                all_links = row.query_selector_all('a')
                article_candidates = []
                
                for link in all_links:
                    href = link.get_attribute('href')
                    text = link.inner_text().strip()
                    
                    if not href:
                        continue
                    
                    print(f"检查链接: 文本='{text[:20]}...', href='{href}'")
                    
                    # 收集所有可能的文章链接
                    if any(pattern in href for pattern in ['/new/', '/detail/', 'mp.weixin.qq.com']):
                        article_candidates.append((href, text))
                
                # 优先处理看起来像文章标题的链接
                for href, text in article_candidates:
                    if _is_valid_title(text, re) and len(text) > 10:
                        print(f"✅ 找到标题链接: {href}")
                        return _resolve_article_url(href, page)
                
                # 如果没有标题链接，尝试第一个非作者链接
                for href, text in article_candidates:
                    if not any(keyword in text for keyword in ['粉丝数', '发布于']):
                        print(f"✅ 尝试非作者链接: {href}")
                        return _resolve_article_url(href, page)
                
                # 方法3：如果都没找到，尝试模拟点击标题区域
                print("尝试通过点击获取链接...")
                title_cells = row.query_selector_all('td:nth-child(2), [class*="title"]')
                for cell in title_cells:
                    try:
                        # 保存当前URL
                        original_url = page.url
                        
                        # 点击标题单元格
                        cell.click()
                        page.wait_for_timeout(3000)
                        
                        # 检查是否跳转
                        current_url = page.url
                        if current_url != original_url:
                            print(f"✅ 通过点击获取链接: {current_url}")
                            
                            # 如果是微信链接，直接返回
                            if 'mp.weixin.qq.com' in current_url:
                                final_url = _extract_wechat_url_from_captcha(current_url)
                                # 返回原页面
                                page.goto(original_url, timeout=30000)
                                page.wait_for_timeout(2000)
                                return final_url
                            else:
                                # 返回原页面
                                page.goto(original_url, timeout=30000)
                                page.wait_for_timeout(2000)
                                return current_url
                        else:
                            # 如果没跳转，返回原页面
                            page.goto(original_url, timeout=30000)
                    except Exception as e:
                        print(f"点击尝试失败: {e}")
                        continue
                
                print("❌ 未找到文章链接")
                return "https://www.newrank.cn"
                
            except Exception as e:
                print(f"提取链接失败: {e}")
                return "https://www.newrank.cn"
        
        def _resolve_article_url(newrank_url, page):
            """解析新榜文章链接获取真实微信文章地址"""
            try:
                print(f"开始解析文章链接: {newrank_url}")
                
                # 确保URL完整
                if not newrank_url.startswith('http'):
                    newrank_url = f"https://www.newrank.cn{newrank_url}"
                
                print(f"访问新榜文章页: {newrank_url}")
                
                # 在新标签页中打开文章页面
                new_page = page.context.new_page()
                new_page.goto(newrank_url, timeout=30000)
                new_page.wait_for_timeout(5000)
                
                # 获取当前URL
                current_url = new_page.url
                print(f"解析后URL: {current_url}")
                
                # 如果是微信验证链接，提取真实URL
                if 'wappoc_appmsgcaptcha' in current_url:
                    real_url = _extract_wechat_url_from_captcha(current_url)
                    new_page.close()
                    return real_url
                
                # 如果是直接微信文章链接
                if 'mp.weixin.qq.com/s?' in current_url:
                    print(f"✅ 找到直接微信文章链接: {current_url}")
                    new_page.close()
                    return current_url
                
                # 查找微信iframe
                wechat_iframe = new_page.query_selector('iframe[src*="mp.weixin.qq.com"]')
                if wechat_iframe:
                    iframe_src = wechat_iframe.get_attribute('src')
                    print(f"✅ 找到微信iframe: {iframe_src}")
                    new_page.close()
                    return iframe_src
                
                # 查找跳转按钮或链接
                wechat_links = new_page.query_selector_all('a[href*="mp.weixin.qq.com"]')
                for link in wechat_links:
                    href = link.get_attribute('href')
                    if href and ('/s?' in href or 'wappoc_appmsgcaptcha' in href):
                        print(f"✅ 找到微信跳转链接: {href}")
                        new_page.close()
                        return _extract_wechat_url_from_captcha(href)
                
                print(f"❌ 未找到微信链接，返回: {current_url}")
                new_page.close()
                return current_url
                    
            except Exception as e:
                print(f"解析文章链接失败: {e}")
                try:
                    new_page.close()
                except:
                    pass
                return "https://www.newrank.cn"
        
        print("开始抓取新榜低粉爆文榜...")
        newrank_list = []
        
        # 从环境变量获取Cookie
        newrank_cookie = os.environ.get('NEWRANK_COOKIE', '')
        
        if not newrank_cookie:
            return [{
                'title': '⚠️ 未设置新榜Cookie',
                'url': 'https://www.newrank.cn/hotInfo?platform=GZH&rankType=3'
            }]
        
        print("使用最终优化方法提取文章标题和链接...")
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # 设置更大的视窗
            page.set_viewport_size({"width": 1920, "height": 1080})
            
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
            timestamp = int(time.time())
            target_url = f"https://www.newrank.cn/hotInfo?platform=GZH&rankType=3&t={timestamp}"
            print("访问低粉爆文榜页面...")
            page.goto(target_url, timeout=60000)
            
            # 等待页面加载
            print("等待榜单数据加载...")
            page.wait_for_timeout(15000)
            
            # 方法：直接从表格中提取前10条
            print("从表格中提取前10条...")
            
            # 查找表格
            table_selectors = ['.ant-table-tbody', 'table tbody', '[class*="table"]']
            table_body = None
            for selector in table_selectors:
                table_body = page.query_selector(selector)
                if table_body:
                    table_text = table_body.inner_text()
                    if any(keyword in table_text for keyword in ['阅读数', '点赞数', '转发数']):
                        print(f"找到榜单表格: {selector}")
                        break
                    else:
                        table_body = None
            
            if table_body:
                rows = table_body.query_selector_all('tr')
                print(f"表格中有 {len(rows)} 行")
                
                # 处理第3-12行（实际的数据行）
                for i in range(2, min(12, len(rows))):
                    row = rows[i]
                    
                    try:
                        # 获取整行文本
                        row_text = row.inner_text()
                        lines = [line.strip() for line in row_text.split('\n') if line.strip()]
                        
                        print(f"第{i+1}行内容: {lines}")
                        
                        # 在行中寻找标题：通常是第二个元素（索引1）
                        if len(lines) > 1:
                            title = lines[1]
                            
                            if _is_valid_title(title, re):
                                # 获取真实的文章链接
                                print(f"正在为标题 '{title}' 提取链接...")
                                article_url = _get_article_url(row, page)
                                
                                newrank_list.append({
                                    'title': title,
                                    'url': article_url
                                })
                                print(f"✅ 提取第{len(newrank_list)}条: {title}")
                                print(f"   最终链接: {article_url}")
                            else:
                                print(f"❌ 标题验证失败: {title}")
                                
                    except Exception as e:
                        print(f"处理第{i+1}行时出错: {e}")
                        continue
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        return newrank_list[:10]
        
    except Exception as e:
        print(f"获取新榜低粉爆文榜出错: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return [{
            'title': '⚠️ 新榜低粉爆文榜获取失败',
            'url': 'https://www.newrank.cn/hotInfo?platform=GZH&rankType=3'
        }]
        
def send_to_feishu(weibo_data, zhihu_data, newrank_data):
    """发送消息到飞书"""
    text_content = "🌐 每日热点速递\n\n"
    
    # 微博部分
    if weibo_data and len(weibo_data) > 0:
        text_content += "【🔥 微博热搜 TOP 10】——————————————————————————\n"
        for i, item in enumerate(weibo_data, 1):
            text_content += f"{i}. {item['title']}\n   🔗 {item['url']}\n"
        text_content += "\n"
    
    # 知乎部分
    if zhihu_data and len(zhihu_data) > 0:
        text_content += "【📚 知乎热榜 TOP 30】——————————————————————————\n"
        for i, item in enumerate(zhihu_data, 1):
            text_content += f"{i}. {item['title']}\n"
            if 'zhihu.com' in item['url']:
                text_content += f"   🔗 {item['url']}\n"
        text_content += "\n"
    
    # 新榜低粉爆文榜部分
    if newrank_data and len(newrank_data) > 0:
        text_content += "【💥 新榜低粉爆文榜 TOP 10】——————————————————————————\n"
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
