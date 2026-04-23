# app.py - كود شغال 100% على Render
from flask import Flask, request, jsonify, render_template_string
import requests
import json
import uuid
import os

app = Flask(__name__)

# ============== البيانات ==============
FAKKA_PRODUCTS = [
    "Fakka_2.5_Unite", "Fakka_4.25_Unite", "Fakka_5_Unite", "Fakka_6_NewUnite",
    "Fakka_7_Unite", "Fakka_9_Unite", "Fakka_10_Unite", "Fakka_10_NewUnite",
    "Fakka_10.5_Unite", "Fakka_11.5_Unite", "Fakka_12_Unite", "Fakka_12.5_Unite",
    "Fakka_13_Unite", "Fakka_13.5_Unite", "Fakka_15_Unite", "Fakka_15_NewUnite",
    "Fakka_15.5_Unite", "Fakka_16.5_Unite", "Fakka_17.5_Unite", "Fakka_19.5_NewUnite",
    "Fakka_20_Unite", "Fakka_26_Unite"
]

MARED_PRODUCTS = ["Mared_10_Minuts", "Mared_10_Flexs", "Mared_10_Social"]
NEW_PRODUCTS = [p for p in FAKKA_PRODUCTS if "NewUnite" in p]
OLD_PRODUCTS = [p for p in FAKKA_PRODUCTS if "NewUnite" not in p] + MARED_PRODUCTS
ALL_PRODUCTS = FAKKA_PRODUCTS + MARED_PRODUCTS

# ============== دوال فودافون ==============
def get_seamless_and_msisdn():
    url = "http://mobile.vodafone.com.eg/checkSeamless/realms/vf-realm/protocol/openid-connect/auth"
    params = {'client_id': "cash-app"}
    headers = {
        'User-Agent': "okhttp/4.12.0", 'Connection': "Keep-Alive", 'Accept-Encoding': "gzip",
        'x-agent-operatingsystem': "16", 'clientId': "AnaVodafoneAndroid", 'Accept-Language': "ar",
        'x-agent-device': "Samsung SM-A165F", 'x-agent-version': "2025.11.1",
        'x-agent-build': "1063", 'digitalId': "", 'device-id': "b26ba335813fad21",
        'If-Modified-Since': "Thu, 02 Apr 2026 09:09:07 GMT"
    }
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    data = resp.json()
    raw_msisdn = data.get("msisdn")
    formatted_msisdn = '0' + raw_msisdn if raw_msisdn and raw_msisdn.startswith('1') else raw_msisdn
    return data.get("seamlessToken"), formatted_msisdn

def get_access_token(seamless_token):
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        'grant_type': "password",
        'client_secret': "b86e30a8-ae29-467a-a71f-65c73f2ff5e3",
        'client_id': "cash-app"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0", 'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip", 'silentLogin': "true", 'CRP': "false",
        'seamlessToken': seamless_token, 'firstTimeLogin': "true", 'x-agent-operatingsystem': "16",
        'clientId': "AnaVodafoneAndroid", 'Accept-Language': "ar",
        'x-agent-device': "Samsung SM-A165F", 'x-agent-version': "2025.11.1",
        'x-agent-build': "1063", 'digitalId': "", 'device-id': "b26ba335813fad21"
    }
    resp = requests.post(url, data=payload, headers=headers, timeout=30)
    return resp.json().get("access_token")

def execute_purchase(product_id, receiver, pin, msisdn_sender, access_token):
    url_order = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    
    payload_order = {
        "channel": {"name": "MobileApp"},
        "orderItem": [{
            "action": "insert", "id": product_id,
            "product": {
                "characteristic": [
                    {"name": "PaymentMethod", "value": "VFCash"},
                    {"name": "USE_EMONEY", "value": "False"},
                    {"name": "MerchantCode", "value": "81841829"}
                ],
                "id": product_id,
                "relatedParty": [
                    {"id": msisdn_sender, "name": "MSISDN", "role": "Subscriber"},
                    {"id": receiver, "name": "Receiver", "role": "Receiver"}
                ]
            },
            "@type": product_id, "eCode": 0
        }],
        "relatedParty": [{"id": pin, "name": "pin", "role": "Requestor"}],
        "@type": "CashFakkaAndMared"
    }
    
    headers_order = {
        'User-Agent': "okhttp/4.12.0", 'Accept': "application/json", 'Accept-Encoding': "gzip",
        'api-host': "ProductOrderingManagement", 'useCase': "CashFakkaAndMared",
        'X-Request-ID': str(uuid.uuid4()), 'device-id': "b26ba335813fad21", 'api-version': "v2",
        'msisdn': msisdn_sender, 'Authorization': f"Bearer {access_token}", 'Accept-Language': "ar",
        'x-agent-operatingsystem': "16", 'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Samsung SM-A165F", 'x-agent-version': "2025.11.1",
        'x-agent-build': "1063", 'digitalId': "", 'Content-Type': "application/json; charset=UTF-8"
    }
    
    resp = requests.post(url_order, data=json.dumps(payload_order), headers=headers_order, timeout=30)
    
    if resp.status_code != 200:
        return {"success": False, "message": f"فشل الاتصال - كود: {resp.status_code}"}
    
    try:
        result = resp.json()
        if "code" in result and result["code"] != "0000":
            return {"success": False, "message": result.get('reason', 'خطأ غير معروف')}
        return {"success": True, "message": "تم إرسال الطلب بنجاح", "receiver": receiver, "sender": msisdn_sender}
    except:
        return {"success": True, "message": "تم الاستلام بنجاح", "receiver": receiver, "sender": msisdn_sender}

# ============== واجهة HTML ==============
HTML_TEMPLATE = '''<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>dar7kk - فكة كاش</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Tahoma,Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px}
.container{max-width:900px;margin:auto;background:white;border-radius:25px;padding:35px;box-shadow:0 25px 50px rgba(0,0,0,0.3)}
h1{color:#667eea;text-align:center;margin-bottom:10px}
.subtitle{text-align:center;color:#888;margin-bottom:30px}
.tabs{display:flex;gap:12px;margin-bottom:25px;border-bottom:2px solid #eee}
.tab{padding:12px 25px;cursor:pointer;background:none;border:none;font-size:16px;color:#666}
.tab.active{color:#667eea;border-bottom:3px solid #667eea;font-weight:bold}
.products-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-bottom:30px;max-height:400px;overflow-y:auto;padding:5px}
.product-card{background:#f8f9fa;border-radius:12px;padding:15px;cursor:pointer;border:2px solid transparent;text-align:center}
.product-card:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.1)}
.product-card.selected{border-color:#667eea;background:#f0f0ff}
.product-name{font-weight:bold;color:#333}
.product-type{font-size:11px;color:#888;margin-top:6px}
.selected-product{background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:15px;border-radius:12px;margin-bottom:25px;text-align:center;font-weight:bold}
.form-group{margin-bottom:20px}
label{display:block;margin-bottom:8px;font-weight:bold;color:#333}
input{width:100%;padding:14px;border:2px solid #e0e0e0;border-radius:12px;font-size:16px}
input:focus{outline:none;border-color:#667eea}
button{width:100%;padding:15px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:12px;font-size:18px;cursor:pointer;font-weight:bold}
button:hover{transform:scale(1.02)}
.result{margin-top:25px;padding:18px;border-radius:12px;display:none}
.result.success{background:#d4edda;color:#155724}
.result.error{background:#f8d7da;color:#721c24}
.result.info{background:#d1ecf1;color:#0c5460}
.footer{margin-top:25px;text-align:center;font-size:11px;color:#aaa;padding-top:15px;border-top:1px solid #eee}
</style>
</head>
<body>
<div class="container">
<h1>💰 dar7kk | فكة كاش</h1>
<div class="subtitle">نظام شراء كروت فكة كاش ورصيد</div>
<div class="tabs">
<button class="tab active" onclick="switchTab(\'new\')">🆕 كروت جديدة</button>
<button class="tab" onclick="switchTab(\'old\')">📦 كروت قديمة</button>
</div>
<div id="newProducts" class="products-list"></div>
<div id="oldProducts" class="products-list" style="display:none;"></div>
<div class="selected-product" id="selectedDisplay">✨ لم يتم اختيار كارت بعد</div>
<form id="purchaseForm">
<input type="hidden" id="selectedProduct">
<div class="form-group"><label>📱 رقم المستلم</label><input type="tel" id="receiver" placeholder="مثال: 01234567890" required></div>
<div class="form-group"><label>🔐 الرقم السري</label><input type="password" id="pin" maxlength="6" placeholder="6 أرقام" required></div>
<button type="submit">💸 تنفيذ الشراء</button>
</form>
<div id="result" class="result"></div>
<div class="footer">dar7kk API | فكة كاش</div>
</div>
<script>
const newProducts = ''' + json.dumps(NEW_PRODUCTS) + ''';
const oldProducts = ''' + json.dumps(OLD_PRODUCTS) + ''';
let selectedProduct = null;

function switchTab(tab){
    const newDiv = document.getElementById("newProducts");
    const oldDiv = document.getElementById("oldProducts");
    const tabs = document.querySelectorAll(".tab");
    tabs.forEach(t => t.classList.remove("active"));
    if(tab === "new"){
        newDiv.style.display = "grid";
        oldDiv.style.display = "none";
        tabs[0].classList.add("active");
    } else {
        newDiv.style.display = "none";
        oldDiv.style.display = "grid";
        tabs[1].classList.add("active");
    }
}

function displayProducts(){
    const newC = document.getElementById("newProducts");
    const oldC = document.getElementById("oldProducts");
    newC.innerHTML = "";
    oldC.innerHTML = "";
    for(let i=0; i<newProducts.length; i++){
        newC.appendChild(createCard(newProducts[i], "جديد"));
    }
    for(let i=0; i<oldProducts.length; i++){
        oldC.appendChild(createCard(oldProducts[i], oldProducts[i].includes("Mared") ? "مارد" : "قديم"));
    }
}

function createCard(p, t){
    const div = document.createElement("div");
    div.className = "product-card";
    div.innerHTML = "<div class=\"product-name\">"+p+"</div><div class=\"product-type\">"+t+"</div>";
    div.onclick = function(){
        document.querySelectorAll(".product-card").forEach(c => c.classList.remove("selected"));
        div.classList.add("selected");
        selectedProduct = p;
        document.getElementById("selectedProduct").value = p;
        document.getElementById("selectedDisplay").innerHTML = "✅ الكارت المختار: "+p;
    };
    return div;
}

function showResult(msg, type){
    const r = document.getElementById("result");
    r.innerHTML = msg;
    r.className = "result "+type;
    r.style.display = "block";
    if(type !== "info") setTimeout(function(){ r.style.display = "none"; }, 8000);
}

document.getElementById("purchaseForm").addEventListener("submit", async function(e){
    e.preventDefault();
    if(!selectedProduct){ showResult("❌ اختار كارت أولاً", "error"); return; }
    const receiver = document.getElementById("receiver").value;
    const pin = document.getElementById("pin").value;
    if(!receiver.match(/^01[0-9]{9}$/)){ showResult("❌ رقم المستلم 11 رقم ويبدأ بـ 01", "error"); return; }
    if(!pin.match(/^[0-9]{6}$/)){ showResult("❌ الرقم السري 6 أرقام", "error"); return; }
    showResult("⏳ جاري التنفيذ...", "info");
    try{
        const res = await fetch("/api/purchase", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product_id: selectedProduct, receiver_number: receiver, pin_code: pin })
        });
        const data = await res.json();
        if(data.success){
            showResult("✅ "+data.message+"<br>📱 الشحن للرقم: "+receiver, "success");
            document.getElementById("pin").value = "";
        } else {
            showResult("❌ "+data.message, "error");
        }
    } catch(e){ showResult("❌ خطأ في الاتصال", "error"); }
});

displayProducts();
</script>
</body>
</html>'''

# ============== نقاط API ==============
@app.route('/')
@app.route('/dar7kk')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/login', methods=['POST'])
def login():
    try:
        seamless_token, msisdn = get_seamless_and_msisdn()
        get_access_token(seamless_token)
        return jsonify({"success": True, "msisdn": msisdn})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 401

@app.route('/api/purchase', methods=['POST'])
def purchase():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        receiver = data.get('receiver_number')
        pin = data.get('pin_code')
        
        seamless_token, msisdn_sender = get_seamless_and_msisdn()
        access_token = get_access_token(seamless_token)
        result = execute_purchase(product_id, receiver, pin, msisdn_sender, access_token)
        
        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/products', methods=['GET'])
def products():
    return jsonify({
        "new_products": NEW_PRODUCTS,
        "old_products": OLD_PRODUCTS
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 dar7kk API running on port {port}")
    app.run(host='0.0.0.0', port=port)