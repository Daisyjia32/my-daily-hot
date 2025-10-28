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
        
        print("使用Playwright访问并提取文章标题...")
        
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
            
            # 保存页面文本用于调试
            page_text = page.inner_text('body')
            print(f"页面文本长度: {len(page_text)}")
            
            # 显示页面内容的前1000字符用于调试
            print("=== 页面内容预览 ===")
            print(page_text[:1000])
            print("===================")
            
            # 方法1：使用更简单的正则表达式匹配
            print("方法1：使用正则匹配...")
            # 匹配模式：数字 + 点 + 任意字符（直到行尾或粉丝数等关键词）
            pattern1 = r'(\d+)\.\s*([^\n]+?)(?=\s+[^\s]+\s+粉丝数|\s*$)'
            matches1 = re.findall(pattern1, page_text)
            print(f"正则方法1匹配到 {len(matches1)} 个")
            
            # 方法2：匹配更宽松的模式
            pattern2 = r'(\d+)\.\s*([^\n]+)'
            matches2 = re.findall(pattern2, page_text)
            print(f"正则方法2匹配到 {len(matches2)} 个")
            
            # 显示匹配结果
            all_matches = matches1 if matches1 else matches2
            for i, (rank, title) in enumerate(all_matches[:10]):
                print(f"匹配 {i+1}: 排名{rank} - {title[:50]}...")
            
            # 提取前10个有效标题
            count = 0
            seen_titles = set()
            
            for rank, title in all_matches:
                if count >= 10:
                    break
                
                title = title.strip()
                # 清理标题：移除可能的多余信息
                title = re.split(r'\s+[^\s]+\s+粉丝数', title)[0]
                title = title.split(' 头条')[0]
                title = title.split(' 原')[0]
                title = title.strip()
                
                if len(title) > 5 and title not in seen_titles:
                    seen_titles.add(title)
                    
                    # 查找链接 - 使用更精确的方法
                    href = ""
                    try:
                        # 方法1：查找包含这个标题的链接
                        title_selector = f'text="{title}"'
                        title_elements = page.query_selector_all(title_selector)
                        
                        for elem in title_elements:
                            link_elem = elem.evaluate_handle('(elem) => elem.closest("a")')
                            if link_elem:
                                href_value = link_elem.get_attribute('href')
                                if href_value:
                                    href = href_value
                                    break
                    except:
                        pass
                    
                    # 如果没找到链接，尝试部分匹配
                    if not href and len(title) > 10:
                        try:
                            partial_title = title[:15]
                            partial_elements = page.query_selector_all(f'text=/.*{re.escape(partial_title)}.*/')
                            for elem in partial_elements:
                                link_elem = elem.evaluate_handle('(elem) => elem.closest("a")')
                                if link_elem:
                                    href_value = link_elem.get_attribute('href')
                                    if href_value:
                                        href = href_value
                                        break
                        except:
                            pass
                    
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
            
            # 备用方案：如果正则匹配失败，使用DOM查询
            if not newrank_list:
                print("使用DOM查询方案...")
                
                # 查找所有可能包含排名的元素
                all_elements = page.query_selector_all('*')
                ranked_elements = []
                
                for element in all_elements:
                    try:
                        text = element.inner_text().strip()
                        # 检查是否以数字加点开头
                        if re.match(r'^\d+\.', text):
                            ranked_elements.append({
                                'element': element,
                                'text': text
                            })
                    except:
                        continue
                
                print(f"DOM查询找到 {len(ranked_elements)} 个带排名的元素")
                
                for item in ranked_elements:
                    if count >= 10:
                        break
                    
                    text = item['text']
                    # 提取标题（移除排名数字）
                    title_match = re.match(r'^\d+\.\s*(.+)', text)
                    if title_match:
                        title = title_match.group(1).strip()
                        # 清理标题
                        title = re.split(r'\s+[^\s]+\s+粉丝数', title)[0]
                        title = title.strip()
                        
                        if len(title) > 5 and title not in seen_titles:
                            seen_titles.add(title)
                            
                            # 查找链接
                            element = item['element']
                            link_elem = element.query_selector('a')
                            href = link_elem.get_attribute('href') if link_elem else ''
                            
                            if href and not href.startswith('http'):
                                full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                            else:
                                full_url = href if href else 'https://www.newrank.cn'
                            
                            newrank_list.append({
                                'title': title,
                                'url': full_url
                            })
                            count += 1
                            print(f"✅ DOM方案第{count}条: {title}")
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
        if not newrank_list:
            return [{
                'title': '⚠️ 页面结构解析失败',
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
