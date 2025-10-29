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
    """抓取新榜低粉爆文榜TOP10 - 精准定位版"""
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
        
        print("使用精准定位方法提取文章标题...")
        
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
            print("访问低粉爆文榜页面...")
            page.goto('https://www.newrank.cn/hotInfo?platform=GZH&rankType=3', timeout=60000)
            
            # 等待页面加载
            print("等待榜单数据加载...")
            page.wait_for_timeout(15000)
            
            # 方法1：先定位榜单表格区域，再提取数据
            print("方法1：定位榜单表格区域...")
            
            # 查找包含"阅读数"、"点赞数"等关键词的表格区域
            table_selectors = [
                '.ant-table-tbody',
                'table tbody',
                '[class*="table"]',
                '[class*="tbody"]'
            ]
            
            table_body = None
            for selector in table_selectors:
                table_body = page.query_selector(selector)
                if table_body:
                    table_text = table_body.inner_text()
                    if any(keyword in table_text for keyword in ['阅读数', '点赞数', '转发数']):
                        print(f"找到榜单表格区域: {selector}")
                        break
                    else:
                        table_body = None
            
            if table_body:
                # 从表格区域提取数据
                rows = table_body.query_selector_all('tr')
                print(f"在表格区域找到 {len(rows)} 行数据")
                
                for i, row in enumerate(rows[:15]):  # 多取几行以防万一
                    try:
                        # 获取整行文本
                        row_text = row.inner_text()
                        lines = [line.strip() for line in row_text.split('\n') if line.strip()]
                        
                        # 分析行结构：应该包含排名、标题、作者、数据等信息
                        if len(lines) >= 4:  # 至少包含排名、标题、作者、数据
                            # 第一行通常是排名和标题的组合
                            first_line = lines[0]
                            
                            # 提取标题：通常是第一行中排名数字之后的部分
                            title_match = re.match(r'^\d+\s*(.+)', first_line)
                            if title_match:
                                title = title_match.group(1).strip()
                            else:
                                # 如果没有匹配到排名数字，尝试第二行作为标题
                                title = lines[1] if len(lines) > 1 else first_line
                            
                            # 验证标题
                            if _is_valid_title(title, re) and len(newrank_list) < 10:
                                # 进一步验证：检查行中是否包含阅读数等数据
                                has_stats = any(any(keyword in line for keyword in ['阅读数', '点赞数', '转发数', '收藏']) for line in lines)
                                
                                if has_stats:
                                    clean_title = re.sub(r'\s+', ' ', title)
                                    newrank_list.append({
                                        'title': clean_title,
                                        'url': 'https://www.newrank.cn'
                                    })
                                    print(f"✅ 表格提取第{len(newrank_list)}条: {clean_title}")
                                    
                    except Exception as e:
                        print(f"处理第{i}行时出错: {e}")
                        continue
            
            # 方法2：如果表格方法失败，使用改进的文本分析方法
            if len(newrank_list) < 10:
                print("方法2：使用改进的文本分析方法...")
                
                # 获取整个页面文本进行分析
                page_text = page.inner_text('body')
                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                
                seen_titles = set()
                count = len(newrank_list)
                
                # 寻找包含"阅读数"关键词的区域，这通常是榜单开始的地方
                start_index = -1
                for i, line in enumerate(lines):
                    if '阅读数' in line and '点赞数' in line and '转发数' in line:
                        start_index = i
                        print(f"找到榜单标题行，索引: {i}")
                        break
                
                if start_index != -1:
                    # 从榜单标题行开始分析
                    i = start_index + 1
                    current_rank = 1
                    
                    while i < len(lines) and count < 10:
                        line = lines[i]
                        
                        # 检查是否是排名数字（严格的排名数字检查）
                        if re.match(r'^(1?[0-9]|2[0-9]|3[0-9]|4[0-9]|50)$', line) and current_rank <= 10:
                            rank_num = int(line)
                            if rank_num == current_rank:
                                # 找到正确排名的行，提取标题
                                title_found = False
                                
                                # 在接下来的3行中寻找标题
                                for j in range(i+1, min(i+4, len(lines))):
                                    potential_title = lines[j]
                                    
                                    if (_is_valid_title(potential_title, re) and 
                                        potential_title not in seen_titles and
                                        not _is_author_line(potential_title, re)):
                                        
                                        clean_title = re.sub(r'\s+', ' ', potential_title)
                                        seen_titles.add(clean_title)
                                        newrank_list.append({
                                            'title': clean_title,
                                            'url': 'https://www.newrank.cn'
                                        })
                                        count += 1
                                        print(f"✅ 精确排名{current_rank}第{count}条: {clean_title}")
                                        title_found = True
                                        i = j
                                        current_rank += 1
                                        break
                                
                                if not title_found:
                                    # 如果没找到标题，继续下一个排名
                                    current_rank += 1
                        
                        i += 1
            
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

def _is_valid_title(line, re_module):
    """判断一行文本是否是有效的文章标题"""
    # 基本长度检查
    if len(line) < 8 or len(line) > 120:
        return False
    
    # 必须包含中文
    if not any('\u4e00' <= char <= '\u9fff' for char in line):
        return False
    
    # 排除明显的非标题内容
    exclude_patterns = [
        r'^粉丝数', r'^发布于', r'^阅读数', r'^点赞数', r'^转发数',
        r'^收藏', r'^更多', r'^登录', r'^注册', r'^新榜',
        r'^头条', r'^原', r'^情感', r'^文摘', r'^科技', r'^美食',
        r'^\d+$', r'^[0-9.,wW\+]+$', r'^http', r'^©', r'^首页'
    ]
    
    for pattern in exclude_patterns:
        if re_module.match(pattern, line):
            return False
    
    # 排除包含作者特征的行
    author_indicators = ['粉丝数', '发布于', '星即理', '再见游戏', '抱雪斋文字考古学']
    if any(indicator in line for indicator in author_indicators):
        return False
    
    # 标题通常包含标点符号
    has_punctuation = any(char in line for char in ['：', '！', '？', '…', '，', '。', '"', '“', '”', '.', '|', '『', '』', '《', '》', '——'])
    
    # 标题通常不包含统计数字模式
    has_stats = bool(re_module.search(r'\d+[万wW]', line)) or bool(re_module.search(r'\d+\.\d+[万wW]?', line))
    
    return has_punctuation and not has_stats

def _is_author_line(line, re_module):
    """判断是否是作者行"""
    author_indicators = ['粉丝数', '发布于', '星即理', '再见游戏', '抱雪斋文字考古学']
    return (any(indicator in line for indicator in author_indicators) or 
            re_module.search(r'粉丝数\d+', line) or
            re_module.search(r'发布于\d{4}-\d{2}-\d{2}', line))

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
