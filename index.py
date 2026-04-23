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

def get_seamless_and_msisdn():
    url = "http://mobile.vodafone.com.eg/checkSeamless/realms/vf-realm/protocol/openid-connect/auth"
    params = {'client_id': "cash-app"}
    headers = {
        'User-Agent': "okhttp/4.12.0", 'Connection': "Keep-Alive", 'Accept-Encoding': "gzip",
        'x-agent-operatingsystem': "16", 'clientId': "AnaVodafoneAndroid", 'Accept-Language': "ar",
        'x-agent-device': "Samsung SM-A165F", 'x-agent-version': "2025.11.1", 'x-agent-build': "1063",
        'digitalId': "", 'device-id': "b26ba335813fad21", 'If-Modified-Since': "Thu, 02 Apr 2026 09:09:07 GMT"
    }
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code != 200:
        raise Exception("فشل الحصول على seamlessToken")
    data = resp.json()
    raw_msisdn = data.get("msisdn")
    formatted_msisdn = '0' + raw_msisdn if (raw_msisdn and raw_msisdn.startswith('1')) else raw_msisdn
    return data.get("seamlessToken"), formatted_msisdn

def get_access_token(seamless_token):
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        'grant_type': "password",
        'client_secret': "b86e30a8-ae29-467a-a71f-65c73f2ff5e3",
        'client_id': "cash-app"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0", 'Accept': "application/json, text/plain, */*", 'Accept-Encoding': "gzip",
        'silentLogin': "true", 'CRP': "false", 'seamlessToken': seamless_token, 'firstTimeLogin': "true",
        'x-agent-operatingsystem': "16", 'clientId': "AnaVodafoneAndroid", 'Accept-Language': "ar",
        'x-agent-device': "Samsung SM-A165F", 'x-agent-version': "2025.11.1", 'x-agent-build': "1063",
        'digitalId': "", 'device-id': "b26ba335813fad21"
    }
    resp = requests.post(url, data=payload, headers=headers)
    if resp.status_code != 200:
        raise Exception("فشل الحصول على access_token")
    return resp.json().get("access_token")

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "API is running! Send a POST request to /recharge"})

@app.route('/recharge', methods=['POST'])
def process_recharge():
    try:
        # استقبال البيانات من الـ Request
        data = request.json
        if not data:
            return jsonify({"error": "يجب إرسال البيانات بصيغة JSON"}), 400
            
        selected_product = data.get("product_id")
        receiver = data.get("receiver")
        pin = data.get("pin")

        # التحقق من صحة البيانات
        if not selected_product or selected_product not in all_products:
            return jsonify({"error": "المنتج غير صحيح أو غير موجود"}), 400
        if not receiver:
            return jsonify({"error": "رقم المستلم مطلوب"}), 400
        if not pin or not str(pin).isdigit() or len(str(pin)) != 6:
            return jsonify({"error": "الرقم السري يجب أن يكون 6 أرقام"}), 400

        # 1. الحصول على الـ Tokens
        seamless_token, msisdn_sender = get_seamless_and_msisdn()
        access_token = get_access_token(seamless_token)
        
        # 2. طلب الشراء
        url_order = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
        payload_order = {
            "channel": {"name": "MobileApp"},
            "orderItem": [{
                "action": "insert",
                "id": selected_product,
                "product": {
                    "characteristic": [
                        {"name": "PaymentMethod", "value": "VFCash"},
                        {"name": "USE_EMONEY", "value": "False"},
                        {"name": "MerchantCode", "value": "81841829"}
                    ],
                    "id": selected_product,
                    "relatedParty": [
                        {"id": msisdn_sender, "name": "MSISDN", "role": "Subscriber"},
                        {"id": receiver, "name": "Receiver", "role": "Receiver"}
                    ]
                },
                "@type": selected_product,
                "eCode": 0
            }],
            "relatedParty": [{"id": str(pin), "name": "pin", "role": "Requestor"}],
            "@type": "CashFakkaAndMared"
        }

        headers_order = {
            'User-Agent': "okhttp/4.12.0", 'Accept': "application/json", 'Accept-Encoding': "gzip",
            'api-host': "ProductOrderingManagement", 'useCase': "CashFakkaAndMared",
            'X-Request-ID': "bb81cbe5-0c77-4673-945e-d2c0de90007a", 'device-id': "b26ba335813fad21",
            'api-version': "v2", 'msisdn': msisdn_sender,
            'Authorization': f"Bearer {access_token}",
            'Accept-Language': "ar", 'x-agent-operatingsystem': "16", 'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "Samsung SM-A165F", 'x-agent-version': "2025.11.1", 'x-agent-build': "1063",
            'digitalId': "", 'Content-Type': "application/json; charset=UTF-8"
        }

        resp = requests.post(url_order, data=json.dumps(payload_order), headers=headers_order)
        
        if resp.status_code == 200:
            result = resp.json()
            if "code" in result and result["code"] != "0000":
                return jsonify({"status": "failed", "reason": result.get('reason', 'خطأ غير معروف'), "vodafone_response": result})
            else:
                return jsonify({
                    "status": "success",
                    "message": "تم إرسال الطلب بنجاح",
                    "receiver": receiver,
                    "sender": msisdn_sender
                })
        else:
            return jsonify({"status": "error", "message": f"فشل الاتصال - كود: {resp.status_code}", "details": resp.text}), resp.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
