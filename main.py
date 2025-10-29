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
    """抓取新榜低粉爆文榜TOP10 - 修复导入问题"""
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
        
        print("使用智能分析方法提取文章标题...")
        
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
            
            # 获取整个页面文本进行分析
            page_text = page.inner_text('body')
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            print(f"页面共 {len(lines)} 行文本")
            
            # 调试：打印前50行看看结构
            print("=== 前50行文本 ===")
            for i, line in enumerate(lines[:50]):
                print(f"{i}: {line}")
            print("=================")
            
            seen_titles = set()
            count = 0
            
            # 方法1：基于排名数字的模式识别
            print("方法1：基于排名数字的模式识别...")
            i = 0
            while i < len(lines) and count < 10:
                line = lines[i]
                
                # 检查是否是排名数字（1-50之间的单个数字）
                if re.match(r'^(1?[0-9]|2[0-9]|3[0-9]|4[0-9]|50)$', line):
                    rank_num = int(line)
                    if 1 <= rank_num <= 50:
                        print(f"找到排名数字: {rank_num}")
                        
                        # 在接下来的5行中寻找标题
                        for j in range(i+1, min(i+6, len(lines))):
                            potential_title = lines[j]
                            
                            if _is_valid_title(potential_title, re):
                                # 进一步验证：检查上下文
                                is_valid = True
                                
                                # 检查下一行是否是作者信息
                                if j + 1 < len(lines):
                                    next_line = lines[j + 1]
                                    if _is_author_line(next_line, re):
                                        is_valid = False
                                
                                # 检查前一行是否包含排除关键词
                                if j > 0:
                                    prev_line = lines[j - 1]
                                    if any(keyword in prev_line for keyword in ['收藏', '更多', '阅读数']):
                                        is_valid = False
                                
                                if is_valid and potential_title not in seen_titles:
                                    clean_title = re.sub(r'\s+', ' ', potential_title)
                                    seen_titles.add(clean_title)
                                    newrank_list.append({
                                        'title': clean_title,
                                        'url': 'https://www.newrank.cn'
                                    })
                                    count += 1
                                    print(f"✅ 排名{rank_num}第{count}条: {clean_title}")
                                    i = j  # 跳到标题位置
                                    break
                
                i += 1
            
            # 方法2：如果还不够，使用简单的标题特征识别
            if count < 10:
                print("方法2：使用标题特征识别...")
                
                for i, line in enumerate(lines):
                    if count >= 10:
                        break
                    
                    if _is_valid_title(line, re) and line not in seen_titles:
                        # 检查上下文
                        context_ok = True
                        
                        # 检查下一行
                        if i + 1 < len(lines):
                            next_line = lines[i + 1]
                            if _is_author_line(next_line, re) or any(keyword in next_line for keyword in ['粉丝数', '发布于']):
                                context_ok = False
                        
                        # 检查前一行
                        if i > 0:
                            prev_line = lines[i - 1]
                            if any(keyword in prev_line for keyword in ['收藏', '更多']):
                                context_ok = False
                        
                        if context_ok:
                            clean_title = re.sub(r'\s+', ' ', line)
                            seen_titles.add(clean_title)
                            newrank_list.append({
                                'title': clean_title,
                                'url': 'https://www.newrank.cn'
                            })
                            count += 1
                            print(f"✅ 特征识别第{count}条: {clean_title}")
            
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
    if len(line) < 10 or len(line) > 100:
        return False
    
    # 必须包含中文
    if not any('\u4e00' <= char <= '\u9fff' for char in line):
        return False
    
    # 排除明显的非标题内容
    exclude_patterns = [
        r'^粉丝数', r'^发布于', r'^阅读数', r'^点赞数', r'^转发数',
        r'^收藏', r'^更多', r'^登录', r'^注册', r'^新榜',
        r'^头条', r'^原', r'^情感', r'^文摘', r'^科技', r'^美食',
        r'^\d+$', r'^[0-9.,wW\+]+$', r'^http'
    ]
    
    for pattern in exclude_patterns:
        if re_module.match(pattern, line):
            return False
    
    # 标题通常包含标点符号
    has_punctuation = any(char in line for char in ['：', '！', '？', '…', '，', '。', '"', '“', '”', '.', '|', '『', '』', '《', '》'])
    
    # 标题通常不包含统计数字模式
    has_stats = bool(re_module.search(r'\d+[万wW]', line)) or bool(re_module.search(r'\d+\.\d+', line))
    
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
