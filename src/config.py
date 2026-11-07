from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; GENERATED=DATA/"generated"; DB=DATA/"customer_feedback.db"; OUTPUT=ROOT/"outputs"
SEED=20261022
PRODUCTS=[("PRD-001","Smartphone","Electronics"),("PRD-002","Wireless Headphones","Electronics"),("PRD-003","Home Appliance","Home"),("PRD-004","Fitness Watch","Wearables"),("PRD-005","Online Subscription","Digital Services")]
CHANNELS=[("CH-001","Survey","Owned"),("CH-002","Review Website","Public"),("CH-003","Support Portal","Owned"),("CH-004","Mobile App","Owned"),("CH-005","Email","Owned")]
THEMES={"Delivery":["delivery","shipping","late","courier","arrived","delay"],"Product Quality":["quality","broken","defective","damaged","works","stopped"],"Customer Support":["support","agent","representative","response","help","ticket"],"Pricing":["price","cost","expensive","charged","billing","refund"],"App Experience":["app","website","login","interface","crash","slow"],"Returns & Refunds":["return","refund","replacement","exchange","cancel"]}
