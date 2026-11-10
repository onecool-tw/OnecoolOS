"""Research-only execution ledger; no live CTA/dashboard writes."""
from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite

@dataclass(frozen=True)
class Observation:
    date: date
    adjusted_open: float
    decision_at_utc: datetime
    cta: str
    flow: bool | None

def evaluate(records, *, fee_bps=0, minimum=252):
    """A decision on session i closes; execute at i+1 open, value at i+2 open.

    Assumes caller has already proven individual market bars and macro vintages
    were observable at each decision timestamp; does NOT perform that proof.
    """
    if not isfinite(fee_bps) or not 0<=fee_bps<10000:
        raise ValueError("invalid execution fee")
    if len(records)<minimum+2:
        raise ValueError("insufficient common sample")
    if any(a.date>=b.date for a,b in zip(records,records[1:])):
        raise ValueError("dates must increase")
    if any(not isfinite(x.adjusted_open) or x.adjusted_open<=0 for x in records):
        raise ValueError("invalid adjusted open")
    if any(x.decision_at_utc.tzinfo is None or x.decision_at_utc.utcoffset().total_seconds()!=0 for x in records):
        raise ValueError("decision timestamp must use UTC")
    if any(x.decision_at_utc.date()<x.date for x in records):
        raise ValueError("decision before session")
    if any(x.flow is None or x.cta not in ("BUY","SELL","WATCH","HOLD") for x in records[:-2]):
        raise ValueError("missing factor or CTA state; fail closed")
    names=("buy_hold","cta","flow","flow_cta")
    nav={name:[1.] for name in names}
    invested={name:False for name in names}
    trades={name:0 for name in names}
    events=[]
    cta_underlying=False
    for i in range(len(records)-2):
        state=records[i]
        if state.decision_at_utc.date()>=records[i+1].date:
            raise ValueError("decision must precede execution session")
        cta=invested["cta"] if state.cta in ("WATCH","HOLD") else state.cta=="BUY"
        if state.cta=="BUY":
            cta_underlying=True
        elif state.cta=="SELL":
            cta_underlying=False
        targets={"buy_hold":True,"cta":cta,"flow":state.flow,"flow_cta":bool(cta_underlying and state.flow)}
        growth=records[i+2].adjusted_open/records[i+1].adjusted_open
        for name in names:
            switching=invested[name]!=targets[name]
            if switching: trades[name]+=1
            invested[name]=targets[name]
            nav[name].append(nav[name][-1]*(1-fee_bps/10000 if switching else 1)*(growth if targets[name] else 1))
        events.append({"decision":state.date.isoformat(),
                       "executed":records[i+1].date.isoformat(),
                       "valued":records[i+2].date.isoformat(),
                       "positions":targets})
    if len(events)<minimum:
        raise ValueError("insufficient common sessions")
    duration=(records[-1].date-records[1].date).days
    if duration<=0: raise ValueError("invalid duration")
    def metrics(values):
        peak=1.
        dd=0.
        for v in values:
            peak=max(peak,v)
            dd=min(dd,v/peak-1)
        return {"total_pct":round((values[-1]-1)*100,3),
                "cagr_pct":round((values[-1]**(365.25/duration)-1)*100,3),
                "max_dd_pct":round(dd*100,3)}
    return {"research_only":True,"eligible_sessions":len(events),
            "first_execution":records[1].date.isoformat(),
            "last_valuation":records[-1].date.isoformat(),
            "trades":trades,"strategies":{k:metrics(v) for k,v in nav.items()},
            "ledger":events}
