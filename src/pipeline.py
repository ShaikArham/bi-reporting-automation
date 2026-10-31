"""CSV -> validation/quarantine -> SQLite -> SQL report -> auditable outputs."""
import csv,hashlib,json,sqlite3,tempfile,os
from collections import Counter
from datetime import date
from decimal import Decimal,InvalidOperation
from pathlib import Path

ORDER_FIELDS=['order_id','customer_id','order_date','amount_eur','refund_eur','status']
CUSTOMER_FIELDS=['customer_id','region']

def read_csv(path,fields):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f)
        if r.fieldnames is None or len(r.fieldnames)!=len(set(r.fieldnames)) or not set(fields).issubset(r.fieldnames):
            raise ValueError(f'{Path(path).name}: missing or duplicate column names')
        rows=[]
        for line,row in enumerate(r,2):
            if None in row or any(row.get(k) is None for k in fields):
                raise ValueError(f'{Path(path).name} row {line}: malformed CSV record')
            rows.append({k:row[k].strip() for k in fields})
        return rows

def money(value):
    try:n=Decimal(value)
    except InvalidOperation as exc:raise ValueError('INVALID_MONEY') from exc
    if not n.is_finite() or n<0 or n.as_tuple().exponent < -2 or n>Decimal('1000000000'):
        raise ValueError('INVALID_MONEY')
    return int(n*100)

def validate(customers,orders,as_of):
    ids=set()
    for c in customers:
        if not c['customer_id'] or not c['region'] or c['customer_id'] in ids:
            raise ValueError('Customer dimension contains empty values or duplicate IDs')
        ids.add(c['customer_id'])
    if not ids or not orders:raise ValueError('Inputs must not be empty')
    counts=Counter(r['order_id'] for r in orders)
    accepted=[];rejected=[]
    for line,row in enumerate(orders,2):
        try:
            if not row['order_id']:raise ValueError('MISSING_ORDER_ID')
            if counts[row['order_id']]>1:raise ValueError('DUPLICATE_ORDER_ID')
            if row['customer_id'] not in ids:raise ValueError('UNKNOWN_CUSTOMER')
            try:day=date.fromisoformat(row['order_date'])
            except ValueError:raise ValueError('INVALID_DATE')
            if day>=as_of:raise ValueError('FUTURE_OR_ASOF_DATE')
            if row['status'] not in ('completed','cancelled'):raise ValueError('INVALID_STATUS')
            amount=money(row['amount_eur']);refund=money(row['refund_eur'])
            if refund>amount:raise ValueError('REFUND_EXCEEDS_AMOUNT')
            accepted.append((row['order_id'],row['customer_id'],day.isoformat(),amount,refund,row['status']))
        except ValueError as exc:
            rejected.append(dict(source_line=line,order_id=row['order_id'],reason=str(exc)))
    return accepted,rejected

def write_csv(path,rows,fields):
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)

def run(data_dir,out_dir,site_dir,sql_path,as_of,max_reject_rate=0.02,synthetic=False):
    if not 0<=max_reject_rate<=1:raise ValueError('Reject threshold must be between 0 and 1')
    data_dir=Path(data_dir);out_dir=Path(out_dir);site_dir=Path(site_dir)
    sources={name:hashlib.sha256((data_dir/name).read_bytes()).hexdigest() for name in ['customers.csv','orders.csv']}
    customers=read_csv(data_dir/'customers.csv',CUSTOMER_FIELDS);orders=read_csv(data_dir/'orders.csv',ORDER_FIELDS)
    accepted,rejected=validate(customers,orders,as_of)
    rejection_rate=len(rejected)/len(orders)
    if not accepted or rejection_rate>max_reject_rate:
        raise ValueError(f'Quality gate failed: {len(rejected)}/{len(orders)} rejected; no new outputs published')
    sql=Path(sql_path).read_text(encoding='utf-8')
    # Build in temporary storage; a failed SQL statement cannot replace existing output files.
    with tempfile.TemporaryDirectory() as folder:
        db=Path(folder)/'warehouse.sqlite'
        with sqlite3.connect(db) as conn:
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('CREATE TABLE customers(customer_id TEXT PRIMARY KEY,region TEXT NOT NULL)')
            conn.execute('CREATE TABLE orders(order_id TEXT PRIMARY KEY,customer_id TEXT NOT NULL REFERENCES customers(customer_id),order_date TEXT NOT NULL,amount_cents INTEGER NOT NULL,refund_cents INTEGER NOT NULL,status TEXT NOT NULL)')
            conn.executemany('INSERT INTO customers VALUES (?,?)',[(c['customer_id'],c['region']) for c in customers])
            conn.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?)',accepted)
            conn.row_factory=sqlite3.Row
            monthly=[dict(r) for r in conn.execute(sql)]
            loaded=conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
        eligible=[r for r in accepted if r[5]=='completed' and r[3]>r[4]]
        expected=sum(r[3]-r[4] for r in eligible)
        expected_months={}
        for r in eligible:
            key=r[2][:7]
            m=expected_months.setdefault(key,dict(month=key,orders=0,gross_cents=0,refund_cents=0,net_cents=0))
            m['orders']+=1;m['gross_cents']+=r[3];m['refund_cents']+=r[4];m['net_cents']+=r[3]-r[4]
        if monthly!=[expected_months[k] for k in sorted(expected_months)] or loaded!=len(accepted):
            raise ValueError('Reconciliation failed; no new outputs published')
        assert len(orders)==len(accepted)+len(rejected)
        result=dict(project='Report Relay',as_of=as_of.isoformat(),synthetic=synthetic,status='WARN' if rejected else 'PASS',input_rows=len(orders),accepted_rows=len(accepted),rejected_rows=len(rejected),eligible_orders=len(eligible),excluded_accepted_rows=len(accepted)-len(eligible),net_cents=expected,max_reject_rate=max_reject_rate,rejection_rate=rejection_rate,source_sha256=sources,sql_sha256=hashlib.sha256(sql.encode()).hexdigest(),monthly=monthly,exceptions=rejected,reasons=dict(sorted(Counter(r['reason'] for r in rejected).items())),stages=[dict(name='Extract',status='PASS',detail=f'{len(customers)} customers; {len(orders)} order rows'),dict(name='Validate',status='WARN' if rejected else 'PASS',detail=f'{len(rejected)} quarantined; {rejection_rate:.2%} vs {max_reject_rate:.2%} limit'),dict(name='Load SQLite',status='PASS',detail=f'{loaded} rows loaded; primary and foreign keys enforced'),dict(name='Aggregate SQL',status='PASS',detail=f'{len(monthly)} monthly report rows'),dict(name='Reconcile',status='PASS',detail=f'{expected} net cents; {len(eligible)} report orders matched Python'),dict(name='Publish',status='PASS',detail='CSV, JSON and static dashboard files generated')])
        out_dir.mkdir(parents=True,exist_ok=True);site_dir.mkdir(parents=True,exist_ok=True)
        downloads=site_dir/'downloads';downloads.mkdir(exist_ok=True)
        # Individual file replacement is atomic. The whole output directory is not a single atomic bundle.
        db_target=out_dir/'warehouse.sqlite'
        with tempfile.NamedTemporaryFile(dir=out_dir,delete=False) as f:
            f.write(db.read_bytes());tmp_db=f.name
        os.replace(tmp_db,db_target)
        for target in [out_dir,downloads]:
            write_csv(target/'monthly_sales.csv',monthly,['month','orders','gross_cents','refund_cents','net_cents'])
            write_csv(target/'exceptions.csv',rejected,['source_line','order_id','reason'])
        payload=json.dumps(result,indent=2,sort_keys=True,ensure_ascii=True)+'\n'
        (out_dir/'run.json').write_text(payload,encoding='utf-8')
        (site_dir/'data.js').write_text('window.REPORT_DATA = '+payload,encoding='utf-8')
    return result
