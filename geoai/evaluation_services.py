from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json

from django.apps import apps
from django.conf import settings
from django.db.models import Count, Q, Avg

from .models import ComplaintAnalysis
from .metrics import load_fusion_metrics


@dataclass
class ModuleResult:
    key: str
    name: str
    score: float
    status: str
    quality: float
    operations: float
    data: float
    facts: list[str]
    recommendations: list[str]

    def as_dict(self):
        return asdict(self)


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 1)


def _pct(num: float, den: float, default: float = 0.0) -> float:
    return (float(num) / float(den) * 100.0) if den else default


def _status(score: float) -> str:
    if score >= 90: return "A’lo"
    if score >= 75: return "Yaxshi"
    if score >= 60: return "Qoniqarli"
    if score >= 40: return "Takomillashtirish kerak"
    return "Kritik"


def _module(key, name, quality, operations, data, facts, recs, weights=(0.45, 0.35, 0.20)):
    score = _clamp(weights[0]*quality + weights[1]*operations + weights[2]*data)
    return ModuleResult(key, name, score, _status(score), _clamp(quality), _clamp(operations), _clamp(data), facts, recs)


def _field_exists(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


def _feedback_stats():
    try:
        Model = apps.get_model('organizations', 'OrganizationPredictionFeedback')
    except LookupError:
        return {"total": 0, "reviewed": 0, "accepted": 0, "corrected": 0, "avg_conf": 0.0}
    qs = Model.objects.all()
    total = qs.count()
    reviewed = accepted = corrected = 0
    if _field_exists(Model, 'expert_status'):
        reviewed = qs.exclude(expert_status__in=['', 'pending', 'unreviewed']).count()
        accepted = qs.filter(expert_status__in=['approved', 'confirmed']).count()
        corrected = qs.filter(expert_status__in=['corrected', 'edited']).count()
    elif _field_exists(Model, 'accepted'):
        accepted = qs.filter(accepted=True).count()
        reviewed = total
        corrected = max(total-accepted, 0)
    conf_field = None
    for candidate in ('confidence', 'predicted_confidence', 'top_confidence'):
        if _field_exists(Model, candidate): conf_field = candidate; break
    avg_conf = qs.aggregate(v=Avg(conf_field))['v'] if conf_field else 0.0
    return {"total": total, "reviewed": reviewed, "accepted": accepted, "corrected": corrected, "avg_conf": float(avg_conf or 0.0)}


def model_diagnostics(metrics: dict) -> list[dict]:
    if not metrics.get('available'):
        return [{"level":"critical","title":"Model metrikalari mavjud emas","detail":metrics.get('message','Model o‘qitilmagan.'),"action":"Avval modelni o‘qiting."}]
    out=[]
    dataset=int(metrics.get('dataset_size',0) or 0)
    test=int(metrics.get('test_size',0) or 0)
    accuracy=float(metrics.get('accuracy',0) or 0)
    f1=float(metrics.get('f1_weighted',0) or 0)
    auc=float(metrics.get('roc_auc_macro_ovr',0) or 0)
    if min(accuracy,f1,auc) >= .99 and test < 100:
        out.append({"level":"warning","title":"Ehtimoliy overfitting yoki optimistik baho","detail":f"Accuracy/F1/ROC-AUC juda yuqori, test hajmi esa atigi {test} ta.","action":"Stratified 5-Fold Cross Validationni ishga tushiring va mustaqil test to‘plamini kengaytiring."})
    if dataset < 200:
        out.append({"level":"warning","title":"Dataset kichik","detail":f"Belgilangan yozuvlar soni {dataset} ta.","action":"Har bir sinf uchun kamida 50–100 ta real, ekspert tasdiqlagan yozuv yig‘ing."})
    rows=metrics.get('classification_rows',[])
    if rows:
        supports=[float(r.get('support',0) or 0) for r in rows]
        if supports and min(supports)>0 and max(supports)/min(supports) >= 3:
            out.append({"level":"warning","title":"Sinflar nomutanosib","detail":f"Eng katta va eng kichik support nisbati {max(supports)/min(supports):.1f} baravar.","action":"Kam namunalangan sinflarga real yozuv qo‘shing yoki stratifikatsiya/class_weight ishlating."})
        weak=sorted(rows,key=lambda r: float(r.get('f1',0) or 0))[:2]
        for r in weak:
            if float(r.get('f1',0) or 0) < .8:
                out.append({"level":"critical","title":f"{r.get('label')} sinfi sust","detail":f"F1={float(r.get('f1',0)):.3f}, support={int(r.get('support',0) or 0)}.","action":"Ushbu sinfdagi xato misollarni ekspert navbatiga yuboring va datasetni kengaytiring."})
    classes=metrics.get('classes',[]); cm=metrics.get('confusion_matrix',[])
    pairs=[]
    for i,row in enumerate(cm):
        for j,val in enumerate(row):
            if i!=j and val:
                pairs.append((int(val), classes[i] if i<len(classes) else str(i), classes[j] if j<len(classes) else str(j)))
    for val,a,b in sorted(pairs, reverse=True)[:3]:
        out.append({"level":"warning","title":f"{a} → {b} chalkashuvi","detail":f"{val} ta test yozuvi noto‘g‘ri {b} sifatida bashorat qilingan.","action":"Ushbu juftlik bo‘yicha xato misollarni eksport qiling, sinonim va label qoidalarini aniqlashtiring."})
    top=metrics.get('top_features',[])
    if top and float(top[0].get('importance',0) or 0) > .30:
        out.append({"level":"warning","title":"Bitta belgi haddan tashqari dominant","detail":f"{top[0].get('feature')} belgisi importance={float(top[0].get('importance',0)):.3f}.","action":"Sinonimlarni kengaytiring va model qarorining birgina belgiga bog‘lanishini tekshiring."})
    if not out:
        out.append({"level":"success","title":"Jiddiy diagnostik muammo topilmadi","detail":"Mavjud metrikalarda kritik signal aniqlanmadi.","action":"Yangi verified ma’lumotlar bilan davriy K-Fold tekshiruvini davom ettiring."})
    return out


def build_evaluation_dashboard() -> dict:
    Report=apps.get_model('reports','Report')
    Assignment=apps.get_model('reports','ReportAssignment')
    Evidence=apps.get_model('reports','ReportWorkEvidence')
    total=Report.objects.count()
    coord=Report.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).count()
    assigned=Assignment.objects.count()
    assigned_reports=Assignment.objects.values('report_id').distinct().count()
    resolved=Report.objects.filter(status='resolved').count()
    in_progress=Report.objects.filter(status='in_progress').count()
    pending=Report.objects.filter(status='pending_confirmation').count()
    confirmed=Report.objects.filter(citizen_confirmed_at__isnull=False).count() if _field_exists(Report,'citizen_confirmed_at') else 0
    deadline_total=Assignment.objects.exclude(deadline_at__isnull=True).count()
    ontime=Assignment.objects.filter(completed_at__isnull=False, deadline_at__isnull=False, completed_at__lte=models.F('deadline_at')).count() if False else 0
    evidence_reports=Evidence.objects.values('report_id').distinct().count()
    analysis=ComplaintAnalysis.objects.count()
    feedback=_feedback_stats()
    metrics=load_fusion_metrics()
    dataset=int(metrics.get('dataset_size',0) or 0) if metrics.get('available') else 0
    accuracy=float(metrics.get('accuracy',0) or 0)*100 if metrics.get('available') else 0
    f1=float(metrics.get('f1_weighted',0) or 0)*100 if metrics.get('available') else 0
    conf=float(feedback.get('avg_conf',0) or 0)
    if conf <= 1: conf*=100

    modules=[]
    modules.append(_module('citizen_bot','Fuqaro Telegram boti', _pct(coord,total), 90 if total else 40, min(100,_pct(total,100)), [f"Jami murojaat: {total}",f"Koordinatali: {coord}"], ["Bekor qilingan va yakunlanmagan bot sessiyalarini alohida log qiling."] if total else ["Pilot murojaatlar bilan oqimni sinang."]))
    modules.append(_module('location','Lokatsiya va manzil tanlash', _pct(coord,total), _pct(coord,total), min(100,_pct(coord,100)), [f"Lokatsiya qamrovi: {_pct(coord,total):.1f}%"], ["Lokatsiyasiz murojaatlarni majburiy ekspert navbatiga yuboring."] if coord<total else ["Manzil qidiruvi va GPS aniqligini davriy audit qiling."]))
    modules.append(_module('classifier','Murojaat klassifikatsiyasi', f1, accuracy, min(100,_pct(dataset,200)), [f"Accuracy: {accuracy:.1f}%",f"Weighted F1: {f1:.1f}%",f"Dataset: {dataset}"], [d['action'] for d in model_diagnostics(metrics)[:2]]))
    accept_rate=_pct(feedback['accepted'],feedback['reviewed']) if feedback['reviewed'] else conf
    modules.append(_module('org_ml','Tashkilotni ML aniqlash', accept_rate, conf, min(100,_pct(feedback['total'],200)), [f"Feedback: {feedback['total']}",f"Ekspert ko‘rgan: {feedback['reviewed']}",f"Qabul qilingan: {feedback['accepted']}"], ["Kam ishonchli va tuzatilgan misollarni verified datasetga qo‘shing."]))
    modules.append(_module('routing','Routing Engine', accept_rate, max(conf,50 if feedback['total'] else 30), min(100,_pct(feedback['total'],300)), [f"Tuzatilgan tavsiyalar: {feedback['corrected']}",f"O‘rtacha confidence: {conf:.1f}%"], ["Multi-label va asosiy/hamkor tashkilot labelini ekspert orqali boyiting."]))
    modules.append(_module('org_dashboard','Tashkilot rahbari kabineti', _pct(resolved,total), 85 if total else 40, min(100,_pct(total,100)), [f"Hal qilingan: {resolved}",f"Jarayonda: {in_progress}",f"Tasdiq kutilmoqda: {pending}"], ["SLA qabul qilish va bajarish vaqtlarini muntazam kuzating."]))
    modules.append(_module('dispatcher','Dispetcher va taqsimlash', _pct(assigned_reports,total), _pct(assigned_reports,total), min(100,_pct(assigned,100)), [f"Biriktirishlar: {assigned}",f"Biriktirilgan murojaatlar: {assigned_reports}"], ["Biriktirilmagan murojaatlar uchun avtomatik ogohlantirish yarating."] if assigned_reports<total else ["Xodim yuklamasi balansini kuzating."]))
    modules.append(_module('worker_web','Xodim web kabineti', _pct(resolved,max(assigned_reports,1)), 85 if assigned else 40, min(100,_pct(assigned,100)), [f"Faol: {in_progress}",f"Yakunlangan: {resolved}"], ["Kunlik/haftalik/yillik filtrlar va kechikkan vazifalar auditini davom ettiring."]))
    modules.append(_module('worker_bot','Xodim Telegram kabineti', _pct(evidence_reports,max(resolved+pending,1)), 80 if assigned else 40, min(100,_pct(evidence_reports,50)), [f"Dalilli murojaatlar: {evidence_reports}",f"Biriktirishlar: {assigned}"], ["Tasdiqlashga yuborishda foto va izoh majburiyligini saqlang."]))
    modules.append(_module('citizen_confirmation','Fuqaro tasdig‘i', _pct(confirmed,max(resolved,1)), _pct(confirmed,max(resolved,1)), min(100,_pct(resolved,50)), [f"Fuqaro tasdiqlagan: {confirmed}",f"Resolved: {resolved}",f"Tasdiq kutilmoqda: {pending}"], ["6/24 soatdan keyin avtomatik eslatma yuborishni qo‘shing."] if pending else ["Tasdiqlash auditini saqlang."]))
    modules.append(_module('geoanalytics','Geoanalitika va monitoring', _pct(analysis,total), _pct(coord,total), min(100,_pct(analysis,200)), [f"GeoAI tahlillar: {analysis}",f"Koordinatali murojaatlar: {coord}"], ["Tahlil qilinmagan yangi murojaatlarni batch rejimda qayta hisoblang."] if analysis<total else ["Risk va hotspot natijalarini vaqt bo‘yicha tekshiring."]))
    review_rate=_pct(feedback['reviewed'],feedback['total']) if feedback['total'] else 0
    modules.append(_module('expert_validation','AI Expert Validation', accept_rate, review_rate, min(100,_pct(feedback['reviewed'],100)), [f"Navbat: {max(feedback['total']-feedback['reviewed'],0)}",f"Ko‘rib chiqilgan: {feedback['reviewed']}",f"Tuzatilgan: {feedback['corrected']}"], ["Past confidence yozuvlarini birinchi o‘ringa qo‘ying."]))

    weights={'classifier':1.3,'org_ml':1.3,'routing':1.3,'citizen_confirmation':1.2,'worker_bot':1.1,'location':1.1}
    total_w=sum(weights.get(m.key,1) for m in modules)
    platform=round(sum(m.score*weights.get(m.key,1) for m in modules)/total_w,1)
    counts={"excellent":sum(m.score>=90 for m in modules),"good":sum(75<=m.score<90 for m in modules),"needs":sum(40<=m.score<75 for m in modules),"critical":sum(m.score<40 for m in modules)}
    recommendations=[]
    for m in sorted(modules,key=lambda x:x.score):
        for r in m.recommendations[:2]:
            recommendations.append({"module":m.name,"score":m.score,"text":r})
    return {"modules":[m.as_dict() for m in modules],"platform_score":platform,"platform_status":_status(platform),"counts":counts,"diagnostics":model_diagnostics(metrics),"recommendations":recommendations[:12],"metrics":metrics}
