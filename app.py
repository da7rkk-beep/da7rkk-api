from flask import Flask, request, jsonify, render_template_string
import requests
import json

app = Flask(__name__)

# ------------------- البيانات (من السكريبت الأصلي) -------------------
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

NEW_PRODUCTS = [p for p in fakka_products if "NewUnite" in p]
OLD_PRODUCTS = [p for p in fakka_products if "NewUnite" not in p] + mared_products

# ------------------- دوال السكريبت الأصلي (من غير تعديل) -------------------
def get_seamless_and_msisdn():
    url = "http://mobile.vodafone.com.eg/checkSeamless/realms/vf-realm/protocol/openid-connect/auth"
    params = {'client_id': "cash-app"}
    headers = {
        'User-Agent': "okhttp/4.12.0", 'Connection': "Keep-Alive", 'Accept-Encoding': "gzip",
        'x-agent-operatingsystem': "16", 'clientId': "AnaVodafoneAndroid", 'Accept-Language': "ar",
        'x-agent-device': "Samsung SM-A165F", 'x-agent-version': "2025.11.1", 'x-agent-build': "1063",
        'digitalId': "", 'device-id': "b26ba335813fad21", 'If-Modified-Since': "Thu, 02 Apr 2026 09:09:07 GMT"
    }
    resp = requests.get(url, params=params, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise Exception("فشل seamlessToken")
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
        'User-Agent': "okhttp/4.12.0", 'Accept': "application/json, text/plain, */*", 'Accept-Encoding': "gzip",
        'silentLogin': "true", 'CRP': "false", 'seamlessToken': seamless_token, 'firstTimeLogin': "true",
        'x-agent-operatingsystem': "16", 'clientId': "AnaVodafoneAndroid", 'Accept-Language': "ar",
        'x-agent-device': "Samsung SM-A165F", 'x-agent-version': "2025.11.1", 'x-agent-build': "1063",
        'digitalId': "", 'device-id': "b26ba335813fad21"
    }
    resp = requests.post(url, data=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise Exception("فشل access_token")
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
        'X-Request-ID': "bb81cbe5-0c77-4673-945e-d2c0de90007a", 'device-id': "b26ba335813fad21",
        'api-version': "v2", 'msisdn': msisdn_sender,
        'Authorization': f"Bearer {access_token}",
        'Accept-Language': "ar", 'x-agent-operatingsystem': "16", 'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Samsung SM-A165F", 'x-agent-version': "2025.11.1", 'x-agent-build': "1063",
        'digitalId': "", 'Content-Type': "application/json; charset=UTF-8"
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

# ------------------- واجهة HTML -------------------
HTML_TEMPLATE = '''<!DOCTYPE html>
<html dir="rtl">
<head><meta charset="UTF-8"><title>dar7kk - فكة كاش</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Tahoma;background:linear-gradient(135deg,#667eea,#764ba2);padding:20px}
.container{max-width:900px;margin:auto;background:#fff;border-radius:25px;padding:35px}
h1{color:#667eea;text-align:center}
.tabs{display:flex;gap:10px;margin:20px 0}
.tab{padding:10px 20px;cursor:pointer;border:none;background:#f0f0f0;border-radius:10px}
.tab.active{background:#667eea;color:#fff}
.products{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin:20px 0}
.card{background:#f8f9fa;padding:12px;border-radius:10px;cursor:pointer;text-align:center}
.card.selected{background:#667eea;color:#fff}
input,button{width:100%;padding:12px;margin:10px 0;border-radius:10px;border:1px solid #ddd}
button{background:#667eea;color:#fff;border:none;cursor:pointer}
.result{margin-top:20px;padding:15px;border-radius:10px;display:none}
.success{background:#d4edda;color:#155724}
.error{background:#f8d7da;color:#721c24}
</style>
</head>
<body>
<div class="container">
<h1>💰 dar7kk | فكة كاش</h1>
<div class="tabs"><button class="tab active" onclick="showTab('new')">🆕 جديدة</button><button class="tab" onclick="showTab('old')">📦 قديمة</button></div>
<div id="newProducts" class="products"></div><div id="oldProducts" class="products" style="display:none"></div>
<div id="selected" style="text-align:center;margin:10px;padding:10px;background:#e7f3ff;border-radius:10px">⭐ لم يتم الاختيار</div>
<input type="hidden" id="product"><input type="tel" id="receiver" placeholder="رقم المستلم"><input type="password" id="pin" placeholder="الرقم السري"><button onclick="buy()">شراء</button>
<div id="result" class="result"></div></div>
<script>
const newP = ''' + json.dumps(NEW_PRODUCTS) + ''';
const oldP = ''' + json.dumps(OLD_PRODUCTS) + ''';
let selected = null;
function showTab(t){
document.getElementById('newProducts').style.display=t=='new'?'grid':'none';
document.getElementById('oldProducts').style.display=t=='old'?'grid':'none';
}
function load(){
let n=document.getElementById('newProducts'),o=document.getElementById('oldProducts');
newP.forEach(p=>{let d=document.createElement('div');d.className='card';d.innerHTML=p;d.onclick=()=>{document.querySelectorAll('.card').forEach(c=>c.classList.remove('selected'));d.classList.add('selected');selected=p;document.getElementById('product').value=p;document.getElementById('selected').innerHTML='✅ '+p;};n.appendChild(d);});
oldP.forEach(p=>{let d=document.createElement('div');d.className='card';d.innerHTML=p;d.onclick=()=>{document.querySelectorAll('.card').forEach(c=>c.classList.remove('selected'));d.classList.add('selected');selected=p;document.getElementById('product').value=p;document.getElementById('selected').innerHTML='✅ '+p;};o.appendChild(d);});
}
async function buy(){
if(!selected){alert('اختار كارت');return;}
let r=document.getElementById('receiver').value,p=document.getElementById('pin').value;
if(!r.match(/^01[0-9]{9}$/)){alert('رقم خاطئ');return;}
if(!p.match(/^[0-9]{6}$/)){alert('الرقم السري 6 ارقام');return;}
let resDiv=document.getElementById('result');
resDiv.innerHTML='⏳ جاري...';resDiv.className='result';resDiv.style.display='block';
try{
let res=await fetch('/api/purchase',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:selected,receiver_number:r,pin_code:p})});
let data=await res.json();
if(data.success){resDiv.innerHTML='✅ '+data.message+'<br>📱 '+r;resDiv.className='result success';document.getElementById('pin').value='';}
else{resDiv.innerHTML='❌ '+data.message;resDiv.className='result error';}
}catch(e){resDiv.innerHTML='❌ خطأ';resDiv.className='result error';}
}
load();
</script></body></html>'''

# ------------------- المسارات -------------------
@app.route('/')
@app.route('/dar7kk')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/purchase', methods=['POST'])
def purchase():
    try:
        data = request.get_json()
        seamless_token, msisdn_sender = get_seamless_and_msisdn()
        access_token = get_access_token(seamless_token)
        result = execute_purchase(data['product_id'], data['receiver_number'], data['pin_code'], msisdn_sender, access_token)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)