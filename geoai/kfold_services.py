from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from django.conf import settings

ML_DIR=Path(settings.BASE_DIR)/'ml'
DATASET_PATH=ML_DIR/'dataset.csv'
RESULT_PATH=ML_DIR/'geoai_kfold_results.json'


def _temporal(series):
    dt=pd.to_datetime(series,errors='coerce').fillna(pd.Timestamp('2026-01-01'))
    month=dt.dt.month.to_numpy(float); dow=dt.dt.dayofweek.to_numpy(float); day=dt.dt.day.to_numpy(float)
    return np.column_stack([np.sin(2*np.pi*month/12),np.cos(2*np.pi*month/12),np.sin(2*np.pi*dow/7),np.cos(2*np.pi*dow/7),day/31])


def _dense(df):
    return np.column_stack([df[['lat','lon']].astype(float).to_numpy(),_temporal(df['time'])])


def run_stratified_kfold(n_splits=5):
    started=time.perf_counter()
    if not DATASET_PATH.exists(): raise FileNotFoundError(f'Dataset topilmadi: {DATASET_PATH}')
    df=pd.read_csv(DATASET_PATH).dropna(subset=['text','category','lat','lon','time']).copy()
    counts=df['category'].astype(str).value_counts()
    if len(df)<20: raise ValueError('K-Fold uchun kamida 20 ta yozuv kerak.')
    if counts.min()<n_splits: raise ValueError(f'Har bir sinfda kamida {n_splits} ta yozuv bo‘lishi kerak. Eng kichik sinf: {counts.min()} ta.')
    y=df['category'].astype(str).to_numpy()
    skf=StratifiedKFold(n_splits=n_splits,shuffle=True,random_state=42)
    folds=[]
    for idx,(tr,te) in enumerate(skf.split(df,y),1):
        train=df.iloc[tr]; test=df.iloc[te]
        vectorizer=TfidfVectorizer(ngram_range=(1,2),min_df=1,sublinear_tf=True)
        scaler=StandardScaler()
        xtr=hstack([vectorizer.fit_transform(train['text'].fillna('').astype(str)),csr_matrix(scaler.fit_transform(_dense(train)))],format='csr')
        xte=hstack([vectorizer.transform(test['text'].fillna('').astype(str)),csr_matrix(scaler.transform(_dense(test)))],format='csr')
        model=RandomForestClassifier(n_estimators=300,random_state=42,class_weight='balanced_subsample',n_jobs=-1)
        model.fit(xtr,y[tr]); pred=model.predict(xte)
        p,r,f,_=precision_recall_fscore_support(y[te],pred,average='weighted',zero_division=0)
        folds.append({'fold':idx,'test_size':len(te),'accuracy':float(accuracy_score(y[te],pred)),'precision_weighted':float(p),'recall_weighted':float(r),'f1_weighted':float(f)})
    def summary(key):
        vals=np.array([x[key] for x in folds],dtype=float)
        return {'mean':float(vals.mean()),'std':float(vals.std(ddof=1) if len(vals)>1 else 0),'min':float(vals.min()),'max':float(vals.max())}
    result={'created_at':datetime.now().isoformat(timespec='seconds'),'n_splits':n_splits,'dataset_size':len(df),'class_counts':counts.to_dict(),'folds':folds,'accuracy':summary('accuracy'),'precision_weighted':summary('precision_weighted'),'recall_weighted':summary('recall_weighted'),'f1_weighted':summary('f1_weighted'),'duration_seconds':float(time.perf_counter()-started)}
    RESULT_PATH.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


def load_kfold_result():
    try: return json.loads(RESULT_PATH.read_text(encoding='utf-8'))
    except Exception: return {}
