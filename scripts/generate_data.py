"""Generate synthetic reporting inputs with deliberate quality defects."""
import csv,random
from datetime import date,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def generate(folder,seed=91):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);rng=random.Random(seed)
    customers=[dict(customer_id=f'C{i:03}',region=rng.choice(['Ireland','UK','EU'])) for i in range(1,61)]
    orders=[]
    for i in range(1,401):
        amount=rng.randint(1000,50000);refund=rng.choice([0,0,0,amount//4,amount])
        orders.append(dict(order_id=f'O{i:04}',customer_id=rng.choice(customers)['customer_id'],order_date=(date(2026,8,1)+timedelta(days=rng.randrange(92))).isoformat(),amount_eur=f'{amount/100:.2f}',refund_eur=f'{refund/100:.2f}',status=rng.choices(['completed','cancelled'],[95,5])[0]))
    for key,value in [('customer_id','MISSING'),('amount_eur','NaN'),('order_date','2026-02-30'),('refund_eur','99999.00')]:
        row=dict(orders[0]);row['order_id']=f'BAD-{key}';row[key]=value;orders.append(row)
    duplicate=dict(orders[1]);orders.append(duplicate)
    for name,rows in [('customers',customers),('orders',orders)]:
        with (folder/f'{name}.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    return customers,orders

if __name__=='__main__':
    c,o=generate(ROOT/'data');print(f'{len(c)} fictional customers, {len(o)} order rows including deliberate defects')
