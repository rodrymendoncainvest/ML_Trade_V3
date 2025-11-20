from typing import List, Optional
def _sma(seq: List[Optional[float]], n: int) -> List[Optional[float]]:
    out=[]; s=0.0; q=[]
    for x in seq:
        q.append(x)
        if len(q)>n:
            y=q.pop(0); s-=0.0 if y is None else y
        if x is not None: s+=x
        out.append(s/n if len(q)==n and all(v is not None for v in q) else None)
    return out
def _ema(seq: List[Optional[float]], n: int) -> List[Optional[float]]:
    out=[]; a=2.0/(n+1.0); ema=None; seed=[]
    for x in seq:
        seed.append(x)
        if ema is None:
            if len(seed)<n: out.append(None); continue
            if len(seed)==n and all(v is not None for v in seed):
                ema=sum(seed)/n; out.append(ema)
            else: out.append(None)
        else:
            if x is None: out.append(ema)
            else: ema=(x-ema)*a+ema; out.append(ema)
    return out
def _rsi_wilder(closes: List[Optional[float]], n: int = 14) -> List[Optional[float]]:
    gains=[0.0]; losses=[0.0]
    for i in range(1,len(closes)):
        if closes[i] is None or closes[i-1] is None: gains.append(0.0); losses.append(0.0); continue
        ch=closes[i]-closes[i-1]; gains.append(max(ch,0.0)); losses.append(max(-ch,0.0))
    avg_g=_ema(gains,n); avg_l=_ema(losses,n); out=[]
    for g,l in zip(avg_g,avg_l):
        if g is None or l is None: out.append(None)
        elif l==0.0: out.append(100.0)
        else: rs=g/l; out.append(100.0-(100.0/(1.0+rs)))
    return out
def _atr(highs,lows,closes,n: int = 14):
    tr=[]; pc=None
    for h,l,c in zip(highs,lows,closes):
        if h is None or l is None: tr.append(None); pc=c; continue
        tr.append(max(h-l, abs(h-(pc if pc is not None else h)), abs(l-(pc if pc is not None else l))))
        pc=c
    return _ema(tr,n)
def build_columns_from_ohlcv(times,opens,highs,lows,closes,volumes,wanted):
    cols=[]; series={}
    if "time" in wanted: cols.append("time"); series["time"]=[float(t) for t in times]
    if "open" in wanted: cols.append("open"); series["open"]=opens
    if "high" in wanted: cols.append("high"); series["high"]=highs
    if "low" in wanted: cols.append("low"); series["low"]=lows
    if "close" in wanted: cols.append("close"); series["close"]=closes
    if "volume" in wanted: cols.append("volume"); series["volume"]=volumes
    def _safe3(a,b,c): return None if (a is None or b is None or c is None) else (a+b+c)/3.0
    def _safe4(a,b,c,d): return None if (a is None or b is None or c is None or d is None) else (a+b+c+d)/4.0
    def _med(a,b): return None if (a is None or b is None) else (a+b)/2.0
    if "hlc3" in wanted or "typical" in wanted:
        v=[_safe3(h,l,c) for h,l,c in zip(highs,lows,closes)]
        if "hlc3" in wanted: cols.append("hlc3"); series["hlc3"]=v
        if "typical" in wanted: cols.append("typical"); series["typical"]=v
    if "ohlc4" in wanted:
        v=[_safe4(o,h,l,c) for o,h,l,c in zip(opens,highs,lows,closes)]
        cols.append("ohlc4"); series["ohlc4"]=v
    if "median" in wanted:
        v=[_med(h,l) for h,l in zip(highs,lows)]
        cols.append("median"); series["median"]=v
    for n in (9,14,20,50,200):
        k=f"sma{n}"
        if k in wanted: cols.append(k); series[k]=_sma(closes,n)
    for n in (9,14,20,50,200):
        k=f"ema{n}"
        if k in wanted: cols.append(k); series[k]=_ema(closes,n)
    if "rsi14" in wanted: cols.append("rsi14"); series["rsi14"]=_rsi_wilder(closes,14)
    if "atr14" in wanted: cols.append("atr14"); series["atr14"]=_atr(highs,lows,closes,14)
    rows=[]
    for i in range(len(times)):
        rows.append([series[c][i] for c in cols])
    return cols, rows
