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
    """抓取新榜低粉爆文榜TOP10 - 点击获取真实链接版"""
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
        
        print("使用Playwright点击获取真实文章链接...")
        
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
            
            # 策略：直接查找榜单中的文章标题并点击获取真实链接
            print("查找榜单中的文章标题元素...")
            
            # 保存当前页面的URL（用于返回）
            original_url = page.url
            
            # 查找所有可能包含文章标题的元素
            all_elements = page.query_selector_all('*')
            potential_titles = []
            
            for element in all_elements:
                try:
                    text = element.inner_text().strip()
                    # 匹配文章标题特征（基于陈道明那条的特征）
                    if (len(text) > 15 and len(text) < 100 and
                        any(char in text for char in ['：', '！', '，', '。', '？', '…']) and
                        not any(keyword in text for keyword in [  # 排除非文章文本
                            '登录', '注册', '首页', '新榜', '轻松', '账号', '找号', '社媒',
                            '营销', '推广', '投放', '创作', '数据', '回采', '作品', '提供',
                            '助力', '增值', '点击', '前往', '正式运营', '办公室'
                        ]) and
                        not re.match(r'^[0-9\.\s]*$', text)):  # 排除纯数字和点
                        
                        potential_titles.append({
                            'text': text,
                            'element': element
                        })
                except:
                    continue
            
            print(f"找到 {len(potential_titles)} 个可能的文章标题")
            
            # 显示前10个用于调试
            for i, title in enumerate(potential_titles[:10]):
                print(f"标题 {i+1}: {title['text']}")
            
            # 尝试点击这些标题来获取真实链接
            count = 0
            seen_titles = set()
            
            for title_info in potential_titles:
                if count >= 10:
                    break
                
                title = title_info['text']
                element = title_info['element']
                
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                
                try:
                    # 点击标题元素
                    print(f"尝试点击: {title}")
                    
                    # 在新标签页中打开链接
                    with page.expect_popup() as popup_info:
                        element.click(button="middle")  # 中键点击在新标签页打开
                    
                    popup = popup_info.value
                    popup.wait_for_load_state()
                    
                    # 获取新标签页的URL
                    popup_url = popup.url
                    print(f"点击后跳转到: {popup_url}")
                    
                    # 检查是否是微信文章链接
                    if 'mp.weixin.qq.com' in popup_url:
                        # 这是真正的微信文章链接！
                        newrank_list.append({
                            'title': title,
                            'url': popup_url
                        })
                        count += 1
                        print(f"✅ 成功获取第{count}条: {title}")
                        print(f"   真实链接: {popup_url}")
                    
                    # 关闭新标签页
                    popup.close()
                    
                    # 等待一下再处理下一个
                    page.wait_for_timeout(1000)
                    
                except Exception as e:
                    print(f"点击失败: {e}")
                    continue
            
            # 如果点击方法失败，使用备用方案：直接解析页面结构
            if not newrank_list:
                print("使用备用方案：直接解析页面结构...")
                
                # 查找包含排名和文章信息的特定结构
                page_text = page.inner_text('body')
                
                # 使用正则表达式匹配排名和标题
                # 匹配模式：数字. 标题（直到粉丝数或阅读数）
                pattern = r'(\d+)\.\s*([^…]+?…|[^…]+?)(?=\s+[^\s]+\s+粉丝数|\s+[0-9Ww\+]+\s*收藏|\s*$)'
                matches = re.findall(pattern, page_text)
                
                print(f"正则匹配到 {len(matches)} 个文章标题")
                
                for rank, title in matches[:10]:
                    title = title.strip()
                    if len(title) > 5 and title not in seen_titles:
                        seen_titles.add(title)
                        
                        # 对于匹配到的标题，我们只能提供新榜页面链接
                        # 因为无法通过简单方法获取微信文章链接
                        newrank_list.append({
                            'title': title,
                            'url': original_url  # 使用原始页面链接
                        })
                        count += 1
                        print(f"✅ 备用方案第{count}条: {title}")
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
        if not newrank_list:
            return [{
                'title': '⚠️ 无法获取文章数据',
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
