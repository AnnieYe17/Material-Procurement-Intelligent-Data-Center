#!/bin/bash

# 进入这个脚本所在的目录（防止双击时路径错乱）
cd "$(dirname "$0")"

echo "📂 当前目录：$(pwd)"

# 激活虚拟环境
source .venv/bin/activate

echo "🐍 Python：$(which python)"
echo "📦 使用 EasyOCR 进行识别..."

# 运行 OCR（识别整个 input_images 文件夹）
python main.py input_images

echo ""
echo "✅ OCR 完成！结果已生成在 output/ 文件夹中"
echo "📄 你可以关闭这个窗口了"
read -n 1 -s -r -p "按任意键退出..."