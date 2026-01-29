# -*- coding: utf-8 -*-
"""
    The spider
"""
import json
import time
import requests
from bs4 import BeautifulSoup
from hscode.row import Hscode, BaseInfo, TaxInfo
from hscode.debug_parse import fetch_and_parse


BASE_URL = 'https://www.hsbianma.com'


def url2html(url, proxy):
    """
      Get the page content of url
    """
    url_link = BASE_URL + url
    if proxy:
        url_link = proxy.replace('{url}', url_link)
    response = requests.get(url_link, timeout=1)
    if response.status_code == 404:
        return ''
    response.encoding = 'utf-8'
    content = response.text
    if not content:
        content = ''
    return str(content)


def parse_code_head_tr(tr_, outdated=False):
    """
        通过每一行记录解析出商品编码并返回
    """
    tds = tr_.find_all('td')
    code_txt = tds[0].text
    code_txt = code_txt.replace(' ', '')
    code_txt = code_txt.replace('\n', '')
    code_txt = code_txt.replace('\r', '')
    code_txt = code_txt.replace('\t', '')
    code_txt = code_txt.replace('.', '')
    if '[过期]' in code_txt:
        if outdated:
            return code_txt[0:-4]
        return None
    return code_txt


def query_hscodes_by_page(chapter, page_index=1, outdated=False, proxy=None):
    """
        search: 搜索条件
        page_index: 页码
        outdated: 是否剔除已过期数据，默认True
        查询每一页的数据
        返回所有的商品编码集合
    """
    url = '/Search/' + str(page_index) + '?keywords=' + str(chapter)
    content = url2html(url, proxy)
    if not content:
        # no response content or 404
        return []
    soup = BeautifulSoup(content, features='lxml')
    all_record_tr = soup.find_all('tr', class_='result-grid')
    if all_record_tr is None:
        return []
    result = []
    for tr_ in all_record_tr:
        code = parse_code_head_tr(tr_, outdated)
        if code:
            result.append(code)
    return result





def search_chapter(chapter, include_outdated=False, quiet=False, proxy=None):
    """
        Search the chapter
    """
    all_code = []
    page_num = 1
    while True:
        print("当前请求页数：" + str(page_num))
        hscodes_per_page = query_hscodes_by_page(chapter, page_num, include_outdated, proxy)
        #没有数据的话就退出
        if len(hscodes_per_page) == 0:
            break
        all_code.extend(hscodes_per_page)
        page_num = page_num + 1
        # 添加延迟以避免请求过于频繁
        time.sleep(2)
    all_code_infos = []
    print("当前的chapter是" + str(chapter) + "  数量是：" + str(len(all_code)))
    #final_arr = all_code[:2]  # 仅处理前5个code以节省时间
    count = len(all_code)
    final_arr = all_code
    for code in final_arr:
        # 解析海关编码
        print('开始请求具体数据数据：',code,'+剩余数量:',count)
        html = BASE_URL + '/Code/' + str(code) + '.html'  
        data = fetch_and_parse(html)
        all_code_infos.append(data)
        count -= 1
        # all_code_infos.append(json.dumps(data, ensure_ascii=False, indent=2))
        time.sleep(2)
    if not quiet:
        print('Item (with searching "' + chapter + '"' + (' including outdated'if include_outdated else '') + ')' + ' num: ' + str(len(all_code)))
    return all_code_infos
