import json,sqlite3
from collections import defaultdict
from sklearn.metrics import accuracy_score,precision_recall_fscore_support
from .config import DB,GENERATED,OUTPUT
def evaluate():
    truth=json.loads((GENERATED/"ground_truth.json").read_text())["expected_labels"];c=sqlite3.connect(DB);pred=defaultdict(dict)
    names={"review":"reviews","survey_response":"survey_responses","support_message":"support_messages"}
    for typ,sid,sent,theme in c.execute("SELECT source_type,source_id,predicted_sentiment,predicted_theme FROM FeedbackAnalysis"):pred[names[typ]][sid]={"sentiment":sent,"theme":theme}
    c.close();report={}
    for kind,labels in truth.items():
        pairs=[(v,pred[kind][rid]) for rid,v in labels.items() if rid in pred[kind]]
        if not pairs:continue
        y=[x[0]["sentiment"] for x in pairs];p=[x[1]["sentiment"] for x in pairs]
        yt=[x[0]["theme"] for x in pairs];pt=[x[1]["theme"] for x in pairs]
        _,_,f,_=precision_recall_fscore_support(y,p,average="macro",zero_division=0)
        _,_,ft,_=precision_recall_fscore_support(yt,pt,average="macro",zero_division=0)
        report[kind]={"records_evaluated":len(pairs),"sentiment_accuracy":round(accuracy_score(y,p),4),"sentiment_macro_f1":round(f,4),"theme_accuracy":round(accuracy_score(yt,pt),4),"theme_macro_f1":round(ft,4)}
    OUTPUT.mkdir(exist_ok=True);(OUTPUT/"evaluation_summary.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return report
if __name__=="__main__":evaluate()
