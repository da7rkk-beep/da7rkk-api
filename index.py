from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "ready", "message": "Vodafone Vercel API is online!"})

@app.route('/charge', methods=['POST'])
def charge():
    try:
        req_data = request.get_json()
        p_id = req_data.get("product_id")
        receiver = req_data.get("receiver")
        pin = req_data.get("pin")
        token = req_data.get("access_token") # التوكن اللي هيبعته موبايلك
        msisdn_sender = req_data.get("msisdn_sender") # رقمك الدافع

        if not all([p_id, receiver, pin, token, msisdn_sender]):
            return jsonify({"error": "بيانات ناقصة، تأكد من إرسال التوكن والرقم السري وكل المطلوبات"}), 400

        # تنفيذ عملية الشراء مباشرة بالتوكن الجاهز
        url_order = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
        payload_order = {
            "channel": {"name": "MobileApp"},
            "orderItem": [{
                "action": "insert", "id": p_id,
                "product": {
                    "characteristic": [
                        {"name": "PaymentMethod", "value": "VFCash"},
                        {"name": "USE_EMONEY", "value": "False"},
                        {"name": "MerchantCode", "value": "81841829"}
                    ],
                    "id": p_id,
                    "relatedParty": [
                        {"id": msisdn_sender, "name": "MSISDN", "role": "Subscriber"},
                        {"id": receiver, "name": "Receiver", "role": "Receiver"}
                    ]
                },
                "@type": p_id, "eCode": 0
            }],
            "relatedParty": [{"id": str(pin), "name": "pin", "role": "Requestor"}],
            "@type": "CashFakkaAndMared"
        }

        headers_order = {
            'User-Agent': "okhttp/4.12.0", 'Authorization': f"Bearer {token}",
            'msisdn': msisdn_sender, 'Content-Type': "application/json"
        }

        final_resp = requests.post(url_order, json=payload_order, headers=headers_order, timeout=15)
        
        # إرجاع رد السيرفر
        return jsonify({"status_code": final_resp.status_code, "response": final_resp.json()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
