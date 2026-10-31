"""Run the fictional BI reporting pipeline. A failed quality gate exits nonzero."""
import argparse,json,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pipeline import run
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=ROOT/'data');p.add_argument('--out',type=Path,default=ROOT/'outputs');p.add_argument('--site',type=Path,default=ROOT/'site');p.add_argument('--sql',type=Path,default=ROOT/'sql/monthly_sales.sql')
    p.add_argument('--as-of',type=date.fromisoformat,default=date(2026,11,1));p.add_argument('--max-reject-rate',type=float,default=0.02);p.add_argument('--synthetic',action='store_true')
    a=p.parse_args()
    try:r=run(a.data,a.out,a.site,a.sql,a.as_of,a.max_reject_rate,a.synthetic)
    except (ValueError,OSError) as exc:p.exit(2,str(exc)+'\n')
    print(json.dumps({k:r[k] for k in ['status','input_rows','accepted_rows','rejected_rows','net_cents']},indent=2))
