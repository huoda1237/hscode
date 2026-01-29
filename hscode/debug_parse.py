import json
import re
import urllib.request
from bs4 import BeautifulSoup


def _text(el) -> str:
    """安全取文本并做轻度清洗（保留中间空格，去掉首尾空白/不可见空格）"""
    if el is None:
        return ""
    return el.get_text(" ", strip=True).replace("\xa0", " ").strip()


def _table_to_kv(box) -> dict:
    """把 cbox 里的 table 解析为 {左列: 右列}"""
    if box is None:
        return {}
    table = box.find("table")
    if table is None:
        return {}

    result = {}
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        k = _text(tds[0])
        v = _text(tds[1])
        # 有些值可能是 '-' '/' 或空，按你的需求可自行转换
        result[k] = v
    return result


def _table_to_code_name_list(box) -> list[dict]:
    """把 cbox 里的 table 解析为 [{code,name}, ...]（如监管/检疫/所属章节/CIQ 等）"""
    if box is None:
        return []
    table = box.find("table")
    if table is None:
        return []

    out = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        code = _text(tds[0])
        name = _text(tds[1])
        if code or name:
            out.append({"code": code, "name": name})
    return out


def _parse_declarations(box) -> list[str]:
    """解析申报要素（右列文本，去掉 [?] 之类的提示）"""
    if box is None:
        return []
    table = box.find("table")
    if table is None:
        return []

    out = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        raw = _text(tds[1])
        # 去掉类似 “[?]” 的提示：可能表现为 '?'、'[]'、或链接文字
        cleaned = re.sub(r"\[\s*\?\s*\]", "", raw)
        cleaned = cleaned.replace("?", "").strip()
        if cleaned:
            out.append(cleaned)
    return out


def _collect_sections(soup) -> dict:
    """
    以 <h3 class="ch3">标题</h3> -> 紧邻的 <div class="cbox"> 方式收集模块
    返回 {标题文本: cbox节点}
    """
    wrap = soup.find(id="wrap") or soup
    sections = {}
    for h3 in wrap.select("h3.ch3"):
        title = _text(h3)
        box = h3.find_next_sibling("div", class_="cbox")
        if title and box is not None:
            sections[title] = box
    return sections


def _find_box(sections: dict, keyword: str):
    """模糊匹配标题包含 keyword 的 cbox"""
    for title, box in sections.items():
        if keyword in title:
            return box
    return None


def parse_hsbianma_html(html: str, source_url: str = "") -> dict:
    soup = BeautifulSoup(html, "lxml")
    sections = _collect_sections(soup)

    # 基本信息
    base_kv = _table_to_kv(_find_box(sections, "基本信息"))
    base_info = {
        "code": base_kv.get("商品编码", ""),
        "name": base_kv.get("商品名称", ""),
        "description": base_kv.get("商品描述", ""),
        "status": base_kv.get("编码状态", ""),
        "update_time": base_kv.get("更新时间", ""),
    }

    # 税率信息（同样按表格 kv 解析）
    tax_kv = _table_to_kv(_find_box(sections, "税率信息"))
    tax_info = {
        "unit": tax_kv.get("计量单位", ""),
        "export_rate": tax_kv.get("出口税率", ""),
        "export_rebate_rate": tax_kv.get("出口退税税率", ""),
        "export_provisional_rate": tax_kv.get("出口暂定税率", ""),
        "vat_rate": tax_kv.get("增值税率", ""),
        "mfn_rate": tax_kv.get("最惠国税率", ""),
        "import_provisional_rate": tax_kv.get("进口暂定税率", ""),
        "import_general_rate": tax_kv.get("进口普通税率", ""),
        "consumption_tax_rate": tax_kv.get("消费税率", ""),
    }

    # 申报要素
    declarations = _parse_declarations(_find_box(sections, "申报要素"))

    # 监管条件 / 检验检疫类别
    supervision_conditions = _table_to_code_name_list(_find_box(sections, "监管条件"))
    quarantine_categories = _table_to_code_name_list(_find_box(sections, "检验检疫类别"))

    # 协定税率 / RCEP税率（输出为 dict）
    agreement_tax_rates_list = _table_to_code_name_list(_find_box(sections, "协定税率"))
    agreement_tax_rates = {x["code"]: x["name"] for x in agreement_tax_rates_list}

    rcep_tax_rates_list = _table_to_code_name_list(_find_box(sections, "RCEP税率"))
    rcep_tax_rates = {x["code"]: x["name"] for x in rcep_tax_rates_list}

    # 所属章节
    chapters = _table_to_code_name_list(_find_box(sections, "所属章节"))

    # CIQ代码(13位海关编码)（输出为 dict）
    ciq_list = _table_to_code_name_list(_find_box(sections, "CIQ代码"))
    ciq_codes = {x["code"]: x["name"] for x in ciq_list}

    return {
        "code": base_kv.get("商品编码", ""),
        "base_info": base_info,
        "tax_info": tax_info,
        "declarations": declarations,
        "supervision_conditions": supervision_conditions,
        "quarantine_categories": quarantine_categories,
        "agreement_tax_rates": agreement_tax_rates,
        "rcep_tax_rates": rcep_tax_rates,
        "chapters": chapters,
        "ciq_codes": ciq_codes,
    }


def fetch_html(url: str, timeout: int = 20) -> str:
    return urllib.request.urlopen(url, timeout=timeout).read().decode("utf-8", "ignore")


def fetch_and_parse(url: str) -> dict:
    html = fetch_html(url)
    return parse_hsbianma_html(html, source_url=url)


if __name__ == "__main__":
    url = "https://hsbianma.com/Code/9403400090.html"
    data = fetch_and_parse(url)
    print(json.dumps(data, ensure_ascii=False, indent=2))