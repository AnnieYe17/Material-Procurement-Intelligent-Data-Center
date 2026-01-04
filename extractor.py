import re
from typing import Optional, Dict, Any


def _to_float(s: str) -> Optional[float]:
    """把字符串安全转成 float；失败就返回 None。"""
    try:
        return float(s)
    except Exception:
        return None


def extract_procurement_fields(raw_text: str) -> Dict[str, Any]:
    """
    从 OCR 的 raw_text 中抽取 MVP 字段：
    item_name, specification, quantity, unit_price, currency, source_text, confidence
    """
    # 0) 预处理：去掉多余空白，按行切分
    text = (raw_text or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # 1) 默认输出（MVP 表结构）
    result = {
        "item_name": None,        # 物料名
        "specification": None,    # 规格（保留“人话”）
        "quantity": None,         # 数量（可为空）
        "unit_price": None,       # 单价（可为空）
        "currency": "CNY",        # 默认人民币
        "source_text": " ".join(lines) if lines else text,
        "confidence": 0.50,       # 先给一个基础分
    }

    if not lines:
        # 没有有效文本，直接返回
        result["confidence"] = 0.0
        return result

    # -----------------------
    # 2) 抽取价格（unit_price）
    # 规则：找 “xx元” 或 “￥xx” 或 “xx块”
    # -----------------------
    price_patterns = [
        r"(?P<price>\d+(?:\.\d+)?)\s*(元|块)\b",
        r"￥\s*(?P<price>\d+(?:\.\d+)?)\b",
        r"RMB\s*(?P<price>\d+(?:\.\d+)?)\b",
    ]

    found_price = None
    for ln in lines:
        for pat in price_patterns:
            m = re.search(pat, ln)
            if m:
                found_price = _to_float(m.group("price"))
                break
        if found_price is not None:
            break

    if found_price is not None:
        result["unit_price"] = found_price
        result["confidence"] += 0.20  # 找到价格，加分

    # currency（非常 MVP：只要出现 $ 就认为 USD，否则默认 CNY）
    if "$" in text or "USD" in text.upper():
        result["currency"] = "USD"

    # -----------------------
    # 3) 抽取规格（specification）
    # 规则：优先找长度/尺寸/功率/型号等典型模式；找到了就把整段当规格
    # 这里先从最常见的 “xx米/m/cm/mm” 开始
    # -----------------------
    spec_patterns = [
        r"\d+(?:\.\d+)?\s*(米|m|M)\b",
        r"\d+(?:\.\d+)?\s*(cm|CM|毫米|mm|MM)\b",
        r"\d+(?:\.\d+)?\s*(瓦|W|w)\b",
        r"(型号|规格|尺寸)\s*[:：]?\s*\S+",
    ]

    found_spec = None
    for ln in lines:
        if any(re.search(pat, ln) for pat in spec_patterns):
            # 简单做法：整行作为规格（保留人类表达，方便回溯）
            found_spec = ln
            break

    # 如果第一行像“灯带3.4米”这种，把“物料名+规格”写在一起，也算规格
    # 但如果我们后面把物料名从中切出来，规格就用剩下部分
    if found_spec is None and len(lines) >= 1:
        # 看第一行是否包含“数字+单位”，如果有，先拿第一行当规格候选
        if re.search(r"\d+(?:\.\d+)?\s*(米|m|cm|mm|瓦|W)\b", lines[0]):
            found_spec = lines[0]

    if found_spec is not None:
        result["specification"] = found_spec
        result["confidence"] += 0.15  # 找到规格，加分

    # -----------------------
    # 4) 抽取数量（quantity）
    # 规则：找 “x个/条/米/套/箱/件/只/根/卷...”
    # 注意：这里很容易跟规格混淆（比如“3.4米”是规格不是数量）
    # 所以 MVP：只抽“个/条/套/箱/件/只/根/卷”等，不抽“米”
    # -----------------------
    qty_patterns = [
        r"(?P<qty>\d+(?:\.\d+)?)\s*(个|条|套|箱|件|只|根|卷)\b",
        r"数量\s*[:：]?\s*(?P<qty>\d+(?:\.\d+)?)\b",
    ]

    found_qty = None
    for ln in lines:
        for pat in qty_patterns:
            m = re.search(pat, ln)
            if m:
                found_qty = _to_float(m.group("qty"))
                break
        if found_qty is not None:
            break

    if found_qty is not None:
        # 数量一般希望是整数，但 MVP 先不强制
        result["quantity"] = found_qty
        result["confidence"] += 0.10

    # -----------------------
    # 5) 抽取物料名（item_name）
    # MVP 启发式：
    # - 优先用第一行
    # - 把第一行里可能属于规格的部分（数字+单位）去掉，剩下当物料名
    # - 再去掉一些“价格/便宜/要不要”等口语
    # -----------------------
    first = lines[0]

    # 去掉常见口语干扰
    noisy_words = ["价格", "便宜", "要不要", "看看", "可以吗", "行不行", "怎么样", "报个价"]
    cleaned = first
    for w in noisy_words:
        cleaned = cleaned.replace(w, "")

    # 去掉“数字+单位”（把规格从第一行剥离出来）
    cleaned = re.sub(r"\d+(?:\.\d+)?\s*(米|m|cm|mm|瓦|W)\b", "", cleaned)
    cleaned = cleaned.strip(" ,，:：-—/")

    # 如果清理完还剩东西，就当物料名；否则退回用第一行（至少不为空）
    if cleaned:
        result["item_name"] = cleaned
        result["confidence"] += 0.15
    else:
        result["item_name"] = first
        result["confidence"] += 0.05

    # -----------------------
    # 6) 最终置信度裁剪到 0~1
    # -----------------------
    result["confidence"] = max(0.0, min(1.0, round(result["confidence"], 2)))

    return result


if __name__ == "__main__":
    sample = "灯带3.4米\n价格已经很便宜了,\n3.8元\n你要不要"
    print(extract_procurement_fields(sample))
