from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhook/feishu", methods=["POST"])
def feishu_webhook():
    data = request.json

    print("👉 收到飞书请求：")
    print(data)

    # 飞书 URL 校验用
    if "challenge" in data:
        return jsonify({
            "challenge": data["challenge"]
        })

    # 普通事件，先只返回成功
    return jsonify({"code": 0})

if __name__ == "__main__":
    app.run(port=3000)