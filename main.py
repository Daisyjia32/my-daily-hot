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
    """抓取新榜低粉爆文榜TOP10 - 通用版本"""
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
        
        print("使用Playwright通用方法提取文章标题...")
        
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
            
            # 策略：基于结构特征提取文章标题
            print("基于结构特征提取文章标题...")
            
            # 方法1：查找包含排名数字和文章标题的特定结构
            print("方法1：查找排名和标题组合...")
            
            # 查找所有包含数字排名的元素
            rank_elements = page.query_selector_all('[class*="rank"], [class*="index"], [class*="number"]')
            print(f"找到 {len(rank_elements)} 个排名元素")
            
            # 如果没有找到专门的排名元素，查找所有包含数字的元素
            if not rank_elements:
                all_elements = page.query_selector_all('*')
                for element in all_elements:
                    text = element.inner_text().strip()
                    if re.match(r'^\d+$', text) and len(text) < 3:  # 单个数字，可能是排名
                        rank_elements.append(element)
                print(f"备用方法找到 {len(rank_elements)} 个排名元素")
            
            count = 0
            seen_titles = set()
            
            # 对于每个排名元素，查找对应的标题
            for rank_element in rank_elements:
                if count >= 10:
                    break
                
                try:
                    rank_text = rank_element.inner_text().strip()
                    if not rank_text.isdigit():
                        continue
                    
                    rank_num = int(rank_text)
                    if rank_num < 1 or rank_num > 50:  # 合理的排名范围
                        continue
                    
                    # 在排名元素附近查找标题
                    # 方法1：查找同一行或相邻元素的标题
                    row_element = rank_element.evaluate_handle('(elem) => elem.closest("tr, div, li")')
                    if row_element:
                        row_text = row_element.as_element().inner_text()
                        
                        # 从行文本中提取标题
                        lines = [line.strip() for line in row_text.split('\n') if line.strip()]
                        
                        for line in lines:
                            # 标题特征：包含中文标点，长度合理，不包含指标关键词
                            if (len(line) > 10 and len(line) < 100 and
                                any(char in line for char in ['：', '！', '？', '…', '，', '。', '"', '“', '”']) and
                                not any(keyword in line for keyword in ['粉丝数', '发布于', '阅读数', '点赞数', '转发数', '收藏', '更多', '登录', '注册']) and
                                not re.match(r'^\d', line) and  # 不以数字开头
                                not re.match(r'^[0-9Ww\+]+$', line)):  # 不是纯数字和W+
                                
                                # 清理标题
                                clean_title = line.split('...')[0].split('…')[0].strip()
                                
                                if clean_title and clean_title not in seen_titles:
                                    seen_titles.add(clean_title)
                                    
                                    # 查找链接
                                    link_elem = row_element.evaluate_handle('(elem) => elem.querySelector("a")')
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
                                    print(f"✅ 排名{rank_num}第{count}条: {clean_title}")
                                    break
                                    
                except Exception as e:
                    continue
            
            # 方法2：如果方法1不够，直接查找所有可能的标题
            if count < 10:
                print("方法2：直接查找所有标题...")
                
                all_elements = page.query_selector_all('*')
                potential_titles = []
                
                for element in all_elements:
                    try:
                        text = element.inner_text().strip()
                        
                        # 标题特征检测
                        is_title = (
                            len(text) > 15 and len(text) < 100 and
                            any(char in text for char in ['：', '！', '？', '…', '，', '。']) and
                            not any(keyword in text for keyword in ['粉丝数', '发布于', '阅读数', '点赞数', '转发数', '收藏', '更多', '登录', '注册', '新榜']) and
                            not text.startswith('http') and
                            not re.match(r'^\d+\.', text) and  # 不以数字加点开头
                            ' ' not in text or len(text.split()) > 2  # 应该是连续文本
                        )
                        
                        if is_title:
                            # 进一步验证：检查是否在表格区域
                            parent = element.evaluate_handle('(elem) => elem.closest("table, tr, .table, .list")')
                            if parent:
                                parent_text = parent.as_element().inner_text()
                                if any(keyword in parent_text for keyword in ['阅读数', '粉丝数', '点赞数']):
                                    potential_titles.append({
                                        'text': text,
                                        'element': element
                                    })
                                    
                    except:
                        continue
                
                print(f"找到 {len(potential_titles)} 个潜在标题")
                
                # 去重并取前10个
                unique_titles = []
                seen_texts = set()
                
                for title_info in potential_titles:
                    text = title_info['text']
                    text_key = text[:30]  # 前30字符去重
                    
                    if text_key not in seen_texts:
                        seen_texts.add(text_key)
                        unique_titles.append(title_info)
                
                for title_info in unique_titles:
                    if count >= 10:
                        break
                    
                    text = title_info['text']
                    element = title_info['element']
                    
                    if text not in seen_titles:
                        seen_titles.add(text)
                        
                        # 查找链接
                        link_elem = element.query_selector('a')
                        href = link_elem.get_attribute('href') if link_elem else ''
                        
                        if href and not href.startswith('http'):
                            full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                        else:
                            full_url = href if href else 'https://www.newrank.cn'
                        
                        newrank_list.append({
                            'title': text,
                            'url': full_url
                        })
                        count += 1
                        print(f"✅ 直接提取第{count}条: {text}")
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
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
