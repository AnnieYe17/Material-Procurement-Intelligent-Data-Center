"""
main.py
用 EasyOCR 在本机（arm64 Mac）做 OCR：图片 -> 识别文字 -> 保存结果
用法：
  python main.py sample.jpg
或：
  python main.py input_images/
"""

import os
import sys
import json
import csv
from datetime import datetime
import easyocr
import pandas as pd
from pathlib import Path

# ✅ 结构化抽取：建议放在文件顶部 import
from extractor import extract_procurement_fields  # 如果你不是这样组织的，看下方“import 怎么改”
from dotenv import load_dotenv
load_dotenv()  # 从 .env 文件加载环境变量

def is_image_file(filename: str) -> bool:
    """判断文件是不是常见图片格式"""
    return filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"))


def ocr_one_image(reader: easyocr.Reader, image_path: str) -> dict:
    """
    对单张图片做 OCR，并返回统一结构的数据（后续抽取/导出都靠它）
    """
    results = reader.readtext(image_path, detail=1)  # [box, text, conf]
    items = []
    for box, text, conf in results:
        text = (text or "").strip()
        if not text:
            continue
        items.append(
            {
                "text": text,
                "conf": float(conf),
            }
        )

    raw_text = "\n".join([x["text"] for x in items])

    return {
        "image": os.path.basename(image_path),
        "path": image_path,
        "raw_text": raw_text,
        "items": items,
    }


def collect_images(path: str) -> list[str]:
    """如果 path 是文件夹，收集里面的图片；如果是文件，就直接返回它"""
    if os.path.isdir(path):
        files = []
        for fn in sorted(os.listdir(path)):
            full = os.path.join(path, fn)
            if os.path.isfile(full) and is_image_file(fn):
                files.append(full)
        return files

    if os.path.isfile(path) and is_image_file(path):
        return [path]

    return []


def export_records_to_csv(records, output_dir="output"):
    """把结构化 records 导出 CSV（Excel 友好）"""
    if not records:
        print("No records to export.")
        return None

    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(output_dir, f"procurement_{ts}.csv")

    fieldnames = [
        "item_name",
        "specification",
        "quantity",
        "unit_price",
        "currency",
        "source_text",
        "confidence",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            row = {k: r.get(k) for k in fieldnames}
            writer.writerow(row)

    print(f"CSV exported to: {csv_path}")
    return csv_path

def csv_to_excel(csv_path: str, xlsx_path: str):
    """
    将 CSV 转换为 Excel 文件
    """
    df = pd.read_csv(csv_path)

    # 写入 Excel
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="采购明细")

        sheet = writer.book["采购明细"]

        # 冻结首行（表头）
        sheet.freeze_panes = "A2"

        # 自动列宽（简单实用版）
        for col in sheet.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            sheet.column_dimensions[col[0].column_letter].width = min(max_length + 2, 40)

def main():
    if len(sys.argv) < 2:
        print("用法：python main.py <图片路径 或 文件夹路径>")
        sys.exit(1)

    input_path = sys.argv[1]
    images = collect_images(input_path)

    if not images:
        print(f"没找到可识别的图片：{input_path}")
        sys.exit(1)

    # 初始化 EasyOCR（中文+英文，适合微信截图混排）
    reader = easyocr.Reader(["ch_sim", "en"])

    outputs = []
    records = []  # ✅ 必须放在循环外，累积所有图片的结果

    for img in images:
        print(f"OCR: {img}")
        out = ocr_one_image(reader, img)
        outputs.append(out)

        # ✅ 抽取采购字段（raw_text -> record）
        record = extract_procurement_fields(out.get("raw_text", ""))
        records.append(record)

    # 把结果保存到 output/ 目录
    os.makedirs("output", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = os.path.join("output", f"ocr_{ts}.json")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(outputs, f, ensure_ascii=False, indent=2)
    print(f"JSON exported to: {out_json}")

    # ✅ 导出 CSV
    csv_path = export_records_to_csv(records)

    if csv_path:
        xlsx_path = csv_path.replace(".csv", ".xlsx")
        csv_to_excel(csv_path, xlsx_path)
        print(f"Excel 已生成：{xlsx_path}")


if __name__ == "__main__":
    main()