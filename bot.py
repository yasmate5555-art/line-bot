# ============================================================
#  bot.py — LINE Bot ด้วย Messaging API (line-bot-sdk v1)
#  ฟีเจอร์: ตอบข้อความอัตโนมัติ, Tag สมาชิกทุกคนในกลุ่ม
# ============================================================

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent
)
import requests, json, os

app = Flask(__name__)

CHANNEL_SECRET       = "f19468a6405de6af58a3f2c59c388229"
CHANNEL_ACCESS_TOKEN = "ANd5CVl8jbfa2kpS8Is23kdpy0z6spiIZ9Aevukjq+5Yj5mbHC17bffj4Vq2ym/I/JW1ROZNh5qPqxze4rNWaed5KpzaCOsjA1oEISIYEBZjwgUkynxtht68BnrnvfWKpu/L36frBT3f/JzjG1E1igdB04t89/1O/w1cDnyilFU="

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(CHANNEL_SECRET)

AUTO_REPLY = {
    "สวัสดี":      "สวัสดีครับ 👋",
    "หวัดดี":      "หวัดดีครับ 😊",
    "บอท":         "มีอะไรให้ช่วยไหมครับ?",
    "ช่วยด้วย":    "บอกมาเลยครับ จะช่วยเต็มที่! 💪",
    "tagall":      "__TAGALL__",
    "แท็กทั้งหมด": "__TAGALL__",
    "แท็กหมด":     "__TAGALL__",
}

def get_group_members(group_id):
    members    = []
    next_token = None
    headers    = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
    while True:
        url    = f"https://api.line.me/v2/bot/group/{group_id}/members/list"
        params = {"start": next_token} if next_token else {}
        res    = requests.get(url, headers=headers, params=params)
        data   = res.json()
        members.extend(data.get("members", []))
        next_token = data.get("next")
        if not next_token:
            break
    return members

def tag_all(reply_token, group_id):
    members = get_group_members(group_id)
    if not members:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="ไม่พบสมาชิกในกลุ่มครับ"))
        return

    headers   = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}", "Content-Type": "application/json"}
    chunks    = [members[i:i+20] for i in range(0, len(members), 20)]
    first     = True

    for chunk in chunks:
        text, mentionees, pos = "", [], 0
        for m in chunk:
            tag = f"@{m.get('displayName','สมาชิก')} "
            mentionees.append({"index": pos, "length": len(tag), "userId": m["userId"], "type": "user"})
            text += tag
            pos  += len(tag)
        if not text:
            continue
        msg = {"type": "text", "text": text, "mentionees": mentionees}
        if first:
            requests.post("https://api.line.me/v2/bot/message/reply",
                headers=headers, data=json.dumps({"replyToken": reply_token, "messages": [msg]}))
            first = False
        else:
            requests.post("https://api.line.me/v2/bot/message/push",
                headers=headers, data=json.dumps({"to": group_id, "messages": [msg]}))

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body      = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text     = event.message.text.strip()
    text_low = text.lower()
    group_id = event.source.group_id if event.source.type == "group" else None

    for keyword, reply in AUTO_REPLY.items():
        if keyword.lower() in text_low:
            if reply == "__TAGALL__":
                if group_id:
                    tag_all(event.reply_token, group_id)
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="ใช้ได้เฉพาะในกลุ่มเท่านั้นครับ"))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

@handler.add(MemberJoinedEvent)
def handle_join(event):
    try:
        names    = [m.display_name for m in event.joined.members if hasattr(m, "display_name") and m.display_name]
        name_str = ", ".join(names) if names else "สมาชิกใหม่"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"ยินดีต้อนรับ {name_str} เข้าสู่กลุ่มครับ! 🎉"))
    except Exception as e:
        print(f"Join error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 40)
    print(f"  LINE Bot กำลังทำงาน port {port}")
    print("  คำสั่ง: tagall / แท็กทั้งหมด / แท็กหมด")
    print("=" * 40)
    app.run(host="0.0.0.0", port=port, debug=False)
