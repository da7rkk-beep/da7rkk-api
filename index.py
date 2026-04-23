from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# قائمة المنتجات
fakka_products = [
    "Fakka_2.5_Unite", "Fakka_4.25_Unite", "Fakka_5_Unite", "Fakka_6_NewUnite",
    "Fakka_7_Unite", "Fakka_9_Unite", "Fakka_10_Unite", "Fakka_10_NewUnite",
    "Fakka_10.5_Unite", "Fakka_11.5_Unite", "Fakka_12_Unite", "Fakka_12.5_Unite",
    "Fakka_13_Unite", "Fakka_13.5_Unite", "Fakka_15_Unite", "Fakka_15_NewUnite",
    "Fakka_15.5_Unite", "Fakka_16.5_Unite", "Fakka_17.5_Unite", "Fakka_19.5_NewUnite",
    "Fakka_20_Unite", "Fakka_26_Unite"
]
mared_products = ["Mared_10_Minuts", "Mared_10_Flexs", "Mared_10_Social"]
all_products = fakka_products + mared_products

def get_tokens():
    # الحصول على التوكنز والدافع تلقائياً من فودافون
    url = "http://mobile.vodafone.com.eg/checkSeamless/realms/vf-realm/protocol/openid-connect/auth"
    params = {'client_id': "cash-app"}
    headers = {'User-Agent': "okhttp/4.12.0", 'clientId': "AnaVodafoneAndroid"}
    
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise Exception("فشل الحصول على Seamless Token - تأكد من الاتصال")
    
    data = resp.json()
    seamless = data.get("seamlessToken")
    raw_msisdn = data.get("msisdn")
    sender = '0' + raw_msisdn if (raw_msisdn and raw_msisdn.startswith('1')) else raw_msisdn

    # تحويل الـ Seamless لـ Access Token
    url_token = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {'grant_type': "password", 'client_secret': "b86e30a8-ae29-467a-a71f-65c73f2ff5e3", 'client_id': "cash-app"}
    headers_token = {'User-Agent': "okhttp/4.12.0", 'seamlessToken': seamless, 'silentLogin': "true"}
    
    resp_token = requests.post(url_token, data=payload, headers=headers_token, timeout=10)
    if resp_token.status_code != 200:
        raise Exception("فشل تحويل التوكن لـ Access Token")
        
    return resp_token.json().get("access_token"), sender

@app.route('/')
def home():
    return jsonify({"status": "ready", "message": "Vodafone API is online!"})

@app.route('/charge', methods=['POST'])
def charge():
    try:
        # استقبال البيانات من المستخدم (رقم المستلم، الباقة، الـ PIN)
        req_data = request.get_json()
        p_id = req_data.get("product_id")
        receiver = req_data.get("receiver")
        pin = req_data.get("pin")

        if not all([p_id, receiver, pin]):
            return jsonify({"error": "Missing data: product_id, receiver, or pin"}), 400

        # جلب التوكنز
        token, msisdn_sender = get_tokens()

        # تنفيذ عملية الشراء
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
        return jsonify({"status_code": final_resp.status_code, "response": final_resp.json()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
