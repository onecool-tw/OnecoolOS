"""Research-only revised-snapshot macro proxy study; NOT point-in-time certified.

Run from repository root (network required):
  python -m research.global_capital_flow_vs_cta.proxy_snapshot_study

Fixed source commits and decision rules; NEVER imports into production.
Uses next-session **close** execution, NOT a next-open trading simulation.
"""
import csv
import io
import json
import math
from datetime import date, timedelta
from pathlib import Path
from urllib.request import urlopen
from onecool_os.market.etf_cta import DailyBar, calculate_cta

PRICES_URL = ("https://raw.githubusercontent.com/manisahni/marketdata/"
              "65a079329e379e104495f459e12e76a8f995585a/daily_adjclose_wide.csv")
MACRO_BASE = ("https://raw.githubusercontent.com/qie2003/treasury-yield-forecast/"
              "b8a6a97aee0589f8932c8f5006ef9b1cf38fdcc5/data/")
LOCAL_0050 = Path("data/market/dashboard/history/0050.csv")
END = date(2026, 7, 30)
START = date(2010, 1, 1)


def read_public_csv(url):
    with urlopen(url, timeout=70) as fh:
        content = fh.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))


def macro_records(rows, column):
    output = [(date.fromisoformat(row["observation_date"]), float(row[column]))
              for row in rows if row[column].strip() not in ("", ".")]
    return [(d, v) for d, v in output if math.isfinite(v) and v > 0 and d <= END]


def prices_for(symbol, wide):
    if symbol == "0050":
        with LOCAL_0050.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        result = [(date.fromisoformat(x["date"]), float(x["adjusted_close"]))
                  for x in rows]
    else:
        result = [(date.fromisoformat(x["Date"]), float(x[symbol]))
                  for x in wide if x.get(symbol)]
    result = [(d,v) for d,v in result if d <= END and v > 0 and math.isfinite(v)]
    if any(x[0] >= y[0] for x,y in zip(result,result[1:])):
        raise ValueError("missing chronological price integrity")
    return result


def signal_panel(symbol, prices, walcl, baa, start=START, walcl_days=9, baa_days=3):
    """Use revised values only after a deliberately assumed observation lag.

    These lags are NOT independently authenticated historical release timestamps.
    WALCL: 13 weekly obs change >=0. BAA10Y: 20 daily obs change <=0.
    Both must hold; no hindsight parameter optimization.
    """
    if walcl_days < 0 or baa_days < 0:
        raise ValueError("negative assumed release lag")
    rows = []
    wj = bj = 0
    for i in range(len(prices) - 2):
        d=prices[i][0]
        if d < start:
            continue
        while wj < len(walcl) and walcl[wj][0] + timedelta(days=walcl_days) <= d:
            wj+=1
        while bj < len(baa) and baa[bj][0] + timedelta(days=baa_days) <= d:
            bj+=1
        if wj < 14 or bj < 21:
            continue
        bars = [DailyBar(trading_date=day,open=v,high=v,low=v,close=v,
                         volume=0,adjusted_close=v)
                for day,v in prices[:i+1]]
        try:
            cta = calculate_cta(symbol,bars).cta
        except Exception as exc:
            # Only explicitly allowed warmup insufficiency may be skipped.
            from onecool_os.market.etf_cta import InsufficientCTAHistory
            if isinstance(exc,InsufficientCTAHistory):
                continue
            raise
        flow = walcl[wj-1][1] >= walcl[wj-14][1] and baa[bj-1][1] <= baa[bj-21][1]
        rows.append((i,cta,flow))
    return rows


def run(symbol, prices, panel, one_way_bps=10):
    if not panel:
        raise ValueError("no eligible decision period")
    if len(panel) < 252:
        raise ValueError("less than 252 eligible decision rows")
    nav={x:[1.] for x in ("buy_hold","cta","macro_proxy","hybrid")}
    in_market={x:False for x in ("cta","macro_proxy","hybrid")}
    trades={x:0 for x in in_market}
    exposures={x:0 for x in in_market}
    underlying_cta=False
    for i,action,flow in panel:
        underlying_cta=(True if action=="BUY" else
                        False if action=="SELL" else underlying_cta)
        goals={"cta":underlying_cta,"macro_proxy":flow,
               "hybrid":underlying_cta and flow}
        growth=prices[i+2][1]/prices[i+1][1]
        nav["buy_hold"].append(nav["buy_hold"][-1]*growth)
        for name,target in goals.items():
            change=target!=in_market[name]
            if change: trades[name]+=1
            in_market[name]=target
            exposures[name]+=int(target)
            nav[name].append(nav[name][-1]*
                             (1-one_way_bps/10000 if change else 1)*
                             (growth if target else 1))
    first=prices[panel[0][0]+1][0]
    last=prices[panel[-1][0]+2][0]
    years=(last-first).days/365.25
    def summary(eq):
        peak=eq[0]
        dd=0.
        for x in eq:
            peak=max(peak,x)
            dd=min(dd,x/peak-1)
        return {"cagr_pct":round((eq[-1]**(1/years)-1)*100,2),
                "max_dd_pct":round(dd*100,2),
                "total_pct":round((eq[-1]-1)*100,2)}
    return {"symbol":symbol,"first_decision":prices[panel[0][0]][0].isoformat(),
            "last_valuation":last.isoformat(),"sessions":len(panel),
            "cost_bps_one_way":one_way_bps,
            "exposure_pct":{k:round(v/len(panel)*100,1) for k,v in exposures.items()},
            "switch_count":trades,
            "strategies":{k:summary(v) for k,v in nav.items()}}


def main():
    wide=read_public_csv(PRICES_URL)
    w=macro_records(read_public_csv(MACRO_BASE+"WALCL.csv"),"WALCL")
    b=macro_records(read_public_csv(MACRO_BASE+"BAA10Y.csv"),"BAA10Y")
    outcomes=[]
    for symbol in ("QQQ","SOXX","0050"):
        prices=prices_for(symbol,wide)
        for start in (date(2010,1,1),date(2019,1,1)):
            panel=signal_panel(symbol,prices,w,b,start=start)
            if not panel: continue
            result=run(symbol,prices,panel)
            result["requested_start"]=start.isoformat()
            outcomes.append(result)
    print(json.dumps({"status":"ASSUMPTION_LAG_REVISED_SNAPSHOT_NOT_PIT",
                      "study":"WALCL(13w)+BAA10Y(20 observations) proxy NOT HY OAS",
                      "assumed_lags_calendar_days":{"WALCL":9,"BAA10Y":3},
                      "price_execution":"signal close -> following session close; next interval return",
                      "price_source":PRICES_URL,"macro_source":MACRO_BASE,
                      "outcomes":outcomes},indent=2))


if __name__=="__main__":
    main()
