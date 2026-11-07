import argparse,csv,json,random
from datetime import datetime,timedelta
from faker import Faker
from .config import GENERATED,SEED,PRODUCTS,CHANNELS,THEMES
fake=Faker()
TEXT={
"Delivery":{"positive":["Delivery was fast and arrived on time.","Shipping was smooth and the courier was helpful."],"negative":["Delivery was late and the delay was frustrating.","My order arrived late and shipping updates were poor."],"neutral":["The order was delivered yesterday.","The package arrived in the afternoon."]},
"Product Quality":{"positive":["The product quality is excellent and it works reliably.","Great quality; I am happy with the product."],"negative":["The product is broken and quality is poor.","The item arrived damaged and stopped working."],"neutral":["I have used the product for two weeks.","The product is available in two sizes."]},
"Customer Support":{"positive":["The support agent was helpful and resolved my issue quickly.","Customer support gave a clear response."],"negative":["Support was slow and the agent did not resolve my issue.","I am disappointed with the poor customer service."],"neutral":["I contacted support about my order.","A support ticket was created yesterday."]},
"Pricing":{"positive":["The price is reasonable and value is great.","Good value for the cost; I am satisfied."],"negative":["The price is expensive and I was charged incorrectly.","Billing was confusing and the cost is too high."],"neutral":["The listed price was shown at checkout.","I reviewed the monthly subscription cost."]},
"App Experience":{"positive":["The app is easy to use and the interface is smooth.","The website works well and login was quick."],"negative":["The app is slow and crashes during login.","The website experience is poor and frustrating."],"neutral":["I used the app to check my account.","The website has an account section."]},
"Returns & Refunds":{"positive":["The return was easy and the refund was quick.","The replacement process was smooth."],"negative":["My refund is late and return process is frustrating.","The replacement has not arrived and cancellation failed."],"neutral":["I submitted a return request.","The refund status is shown in my account."]}}
MIXED=["The product is great, but delivery was late and support was slow.","The app is easy to use, although the refund process was frustrating.","Quality is good, but the price is expensive."]
MULTI=["Delivery bahut late tha, but product quality is good.","El servicio fue lento, pero el producto funciona bien."]
def save(name,rows):
    if not rows:return
    with (GENERATED/f"{name}.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reviews",type=int,default=2500);p.add_argument("--responses",type=int,default=2500);p.add_argument("--messages",type=int,default=1000);p.add_argument("--seed",type=int,default=SEED)
    a=p.parse_args();random.seed(a.seed);Faker.seed(a.seed);fake.seed_instance(a.seed);GENERATED.mkdir(parents=True,exist_ok=True)
    customers=[{"customer_id":f"CUS-{i:06d}","customer_name":fake.name(),"region":random.choice(["North","South","East","West"]),"created_at":"2026-01-01"} for i in range(1,5001)]
    products=[dict(product_id=x[0],product_name=x[1],category=x[2]) for x in PRODUCTS]
    channels=[dict(channel_id=x[0],channel_name=x[1],channel_type=x[2]) for x in CHANNELS]
    surveys=[{"survey_id":f"SUR-2026-{i:06d}","survey_name":n,"product_id":PRODUCTS[(i-1)%5][0],"channel_id":"CH-001","start_date":"2026-01-01","end_date":"2026-12-31","status":"active"} for i,n in enumerate(["Post Purchase","Customer Satisfaction","Support Follow-up"],1)]
    themes=[{"theme_id":f"THEME-{i:06d}","theme_name":n,"description":f"Feedback about {n}"} for i,n in enumerate(THEMES,1)]
    sentiments=[{"sentiment_id":f"SENT-{i:03d}","label":s} for i,s in enumerate(["positive","negative","neutral","mixed"],1)]
    truth={"seed":a.seed,"anomalies":[],"expected_labels":{"reviews":{},"survey_responses":{},"support_messages":{}}}
    def sample():
        theme=random.choice(list(THEMES));sent=random.choices(["positive","negative","neutral","mixed"],[.34,.34,.22,.10])[0]
        txt=random.choice(MIXED) if sent=="mixed" else random.choice(MULTI) if random.random()<.02 else random.choice(TEXT[theme][sent])
        return theme,sent,txt
    start=datetime(2026,1,1);reviews=[];responses=[];messages=[]
    for i in range(1,a.reviews+1):
        th,se,tx=sample();rid=f"REV-2026-{i:06d}"
        reviews.append({"review_id":rid,"customer_id":random.choice(customers)["customer_id"],"product_id":random.choice(products)["product_id"],"channel_id":random.choice(["CH-002","CH-004"]),"review_date":(start+timedelta(days=random.randint(0,308))).date().isoformat(),"rating":{"positive":5,"negative":1,"neutral":3,"mixed":3}[se],"review_text":tx,"source_language":"mixed" if "bahut" in tx or "servicio" in tx else "en","issue_type":""})
        truth["expected_labels"]["reviews"][rid]={"sentiment":se,"theme":th}
    for i in range(1,a.responses+1):
        th,se,tx=sample();sid=random.choice(surveys)["survey_id"];rid=f"RESP-{sid}-{i:06d}"
        responses.append({"response_id":rid,"survey_id":sid,"customer_id":random.choice(customers)["customer_id"],"product_id":random.choice(products)["product_id"],"response_date":(start+timedelta(days=random.randint(0,308))).date().isoformat(),"response_text":tx,"issue_type":""})
        truth["expected_labels"]["survey_responses"][rid]={"sentiment":se,"theme":th}
    for i in range(1,a.messages+1):
        th,se,tx=sample();ticket=f"TKT-2026-{i:06d}";rid=f"MSG-{ticket}-001"
        messages.append({"message_id":rid,"ticket_id":ticket,"customer_id":random.choice(customers)["customer_id"],"product_id":random.choice(products)["product_id"],"channel_id":random.choice(["CH-003","CH-005"]),"message_date":(start+timedelta(days=random.randint(0,308))).date().isoformat(),"message_text":tx,"ticket_status":random.choice(["open","in_progress","closed"]),"issue_type":""})
        truth["expected_labels"]["support_messages"][rid]={"sentiment":se,"theme":th}
    if reviews:
        reviews[0]["issue_type"]="label_text_contradiction";truth["anomalies"].append({"record_type":"review","record_id":reviews[0]["review_id"],"issue_type":"label_text_contradiction","expected_handling":"human review"})
    if len(responses)>1:
        dup=dict(responses[1]);dup["response_id"]=responses[0]["response_id"];dup["issue_type"]="duplicate_response";responses.append(dup)
        truth["anomalies"].append({"record_type":"survey_response","record_id":dup["response_id"],"issue_type":"duplicate_response","expected_handling":"reject duplicate key"})
    if messages:
        messages[0]["message_text"]+=" Customer email: private@example.test";messages[0]["issue_type"]="possible_pii"
        truth["anomalies"].append({"record_type":"support_message","record_id":messages[0]["message_id"],"issue_type":"possible_pii","expected_handling":"redact and flag"})
    if len(reviews)>2:
        reviews[2]["issue_type"]="theme_outside_taxonomy";truth["anomalies"].append({"record_type":"review","record_id":reviews[2]["review_id"],"issue_type":"theme_outside_taxonomy","expected_handling":"flag unmapped theme"})
    if len(messages)>2:
        messages[2]["issue_type"]="test_label_in_input";truth["anomalies"].append({"record_type":"support_message","record_id":messages[2]["message_id"],"issue_type":"test_label_in_input","expected_handling":"never use ground truth as input"})
    for n,r in [("customers",customers),("products",products),("channels",channels),("surveys",surveys),("themes",themes),("sentiment_labels",sentiments),("reviews",reviews),("survey_responses",responses),("support_messages",messages)]:save(n,r)
    (GENERATED/"ground_truth.json").write_text(json.dumps(truth,indent=2),encoding="utf-8")
    print(f"Generated {len(reviews)} reviews, {len(responses)} survey responses, {len(messages)} support messages.")
if __name__=="__main__":main()
