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
    """抓取新榜低粉爆文榜TOP10 - 等待特定内容版"""
    try:
        from playwright.sync_api import sync_playwright
        
        print("开始抓取新榜低粉爆文榜...")
        newrank_list = []
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 访问新榜页面
            print("正在访问新榜页面...")
            page.goto('https://www.newrank.cn/hotInfo?platform=GZH&rankType=3', timeout=60000)
            
            # 等待更长时间，确保动态内容加载
            print("等待动态内容加载...")
            page.wait_for_timeout(15000)
            
            # 方法1：等待特定的低粉爆文榜内容出现
            print("=== 等待低粉爆文榜内容 ===")
            
            # 尝试等待包含公众号文章的元素出现
            try:
                # 等待可能包含公众号文章的区域
                page.wait_for_selector('[class*="weui-media-box"], [class*="list-item"], [class*="rank-item"]', timeout=10000)
                print("检测到文章区域")
            except:
                print("未检测到标准文章区域，继续...")
            
            # 获取页面所有文本，检查是否包含"低粉爆文"相关内容
            page_text = page.inner_text('body')
            if '低粉爆文' in page_text:
                print("页面包含'低粉爆文'内容")
            else:
                print("页面不包含'低粉爆文'内容")
            
            # 方法2：查找所有包含公众号相关文本的元素
            print("=== 查找公众号相关内容 ===")
            
            # 查找所有包含"阅读"、"在看"等公众号指标的元素
            wechat_indicators = ['阅读', '在看', '点赞', '公众号', '微信', 'WX']
            wechat_elements = []
            
            all_elements = page.query_selector_all('div, li, article, section')
            for elem in all_elements:
                text = elem.inner_text().strip()
                if any(indicator in text for indicator in wechat_indicators) and len(text) > 20:
                    wechat_elements.append(elem)
            
            print(f"找到 {len(wechat_elements)} 个包含公众号指标的元素")
            
            # 从这些元素中提取标题和链接
            for i, elem in enumerate(wechat_elements[:20]):  # 只检查前20个
                try:
                    # 在元素内查找标题和链接
                    title_elem = elem.query_selector('h1, h2, h3, h4, [class*="title"], [class*="name"]')
                    link_elem = elem.query_selector('a')
                    
                    if title_elem and link_elem:
                        title = title_elem.inner_text().strip()
                        href = link_elem.get_attribute('href') or ''
                        
                        if title and len(title) > 5 and len(title) < 80:
                            # 构建完整链接
                            if href and not href.startswith('http'):
                                full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                            else:
                                full_url = href
                            
                            # 检查是否是公众号文章链接
                            if full_url and ('wx.' in full_url or 'mp.weixin' in full_url or 'qq.com' in full_url):
                                newrank_list.append({
                                    'title': title,
                                    'url': full_url
                                })
                                print(f"公众号文章 {len(newrank_list)}: {title}")
                            
                            if len(newrank_list) >= 10:
                                break
                                
                except Exception as e:
                    continue
            
            # 方法3：如果还没找到，尝试直接搜索包含特定结构的元素
            if len(newrank_list) < 5:
                print("=== 尝试直接搜索文章结构 ===")
                
                # 查找可能包含文章标题和阅读数的组合
                potential_articles = page.query_selector_all('.weui-media-box, .list-item, [class*="media"], [class*="article"]')
                print(f"找到 {len(potential_articles)} 个可能文章元素")
                
                for article in potential_articles[:15]:
                    if len(newrank_list) >= 10:
                        break
                        
                    try:
                        # 获取整个文章的文本
                        article_text = article.inner_text().strip()
                        
                        # 如果包含阅读数等指标，可能是公众号文章
                        if '阅读' in article_text and '在看' in article_text:
                            # 提取标题（通常是第一行或最突出的文本）
                            lines = [line.strip() for line in article_text.split('\n') if line.strip()]
                            if lines:
                                title = lines[0]
                                if len(title) > 5 and len(title) < 80:
                                    # 查找链接
                                    link_elem = article.query_selector('a')
                                    href = link_elem.get_attribute('href') if link_elem else ''
                                    
                                    if href and not href.startswith('http'):
                                        full_url = f"https://www.newrank.cn{href}" if href.startswith('/') else f"https://www.newrank.cn/{href}"
                                    else:
                                        full_url = href
                                    
                                    if full_url:
                                        newrank_list.append({
                                            'title': title,
                                            'url': full_url
                                        })
                                        print(f"低粉爆文 {len(newrank_list)}: {title}")
                                        
                    except Exception as e:
                        continue
            
            browser.close()
        
        print(f"成功获取新榜数据 {len(newrank_list)} 条")
        
        if not newrank_list:
            return [{
                'title': '⚠️ 页面可能需要登录或内容加载方式特殊',
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
        text_content += "📚 知乎热榜 TOP 10\n"
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
