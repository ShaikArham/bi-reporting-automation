import csv,json,sqlite3,sys,tempfile,unittest
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from pipeline import run,validate,money,read_csv,ORDER_FIELDS
from generate_data import generate
CUSTOMERS=[dict(customer_id='C1',region='Ireland')]
def row(**kw):
    r=dict(order_id='O1',customer_id='C1',order_date='2026-10-01',amount_eur='10.00',refund_eur='2.00',status='completed');r.update(kw);return r
class PipelineTests(unittest.TestCase):
    as_of=date(2026,11,1)
    def test_exact_money_and_invalid_values(self):
        self.assertEqual(money('12.34'),1234)
        for value in ['NaN','Infinity','-1','1.001','1000000001','bad']:
            with self.subTest(value=value),self.assertRaises(ValueError):money(value)
    def test_duplicate_ids_quarantine_all_occurrences(self):
        accepted,rejected=validate(CUSTOMERS,[row(),row(amount_eur='20')],self.as_of)
        self.assertEqual(accepted,[]);self.assertEqual([r['reason'] for r in rejected],['DUPLICATE_ORDER_ID']*2)
    def test_invalid_date_and_asof_boundary(self):
        for value,reason in [('2026-02-30','INVALID_DATE'),('2026-11-01','FUTURE_OR_ASOF_DATE')]:
            _,rejected=validate(CUSTOMERS,[row(order_date=value)],self.as_of);self.assertEqual(rejected[0]['reason'],reason)
    def test_unknown_customer_status_and_refund(self):
        for kw,reason in [({'customer_id':'X'},'UNKNOWN_CUSTOMER'),({'status':'other'},'INVALID_STATUS'),({'refund_eur':'11'},'REFUND_EXCEEDS_AMOUNT')]:
            _,rejected=validate(CUSTOMERS,[row(**kw)],self.as_of);self.assertEqual(rejected[0]['reason'],reason)
    def test_dimension_duplicates_fail(self):
        with self.assertRaises(ValueError):validate(CUSTOMERS*2,[row()],self.as_of)
    def test_empty_inputs_fail(self):
        with self.assertRaises(ValueError):validate(CUSTOMERS,[],self.as_of)
    def test_bad_csv_structure_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.csv';p.write_text('order_id,order_id\nO1,O2\n')
            with self.assertRaises(ValueError):read_csv(p,ORDER_FIELDS)
    def setup_data(self,d):
        data=Path(d)/'data';generate(data);return data,Path(d)/'out',Path(d)/'site'
    def test_sample_reconciles_sql_and_warehouse(self):
        with tempfile.TemporaryDirectory() as d:
            data,out,site=self.setup_data(d);r=run(data,out,site,ROOT/'sql/monthly_sales.sql',self.as_of,synthetic=True)
            self.assertEqual((r['input_rows'],r['accepted_rows'],r['rejected_rows']),(405,399,6))
            self.assertEqual(r['net_cents'],7089413);self.assertEqual(r['status'],'WARN')
            self.assertEqual(sum(m['net_cents'] for m in r['monthly']),r['net_cents'])
            with sqlite3.connect(out/'warehouse.sqlite') as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0],399)
            self.assertEqual(r['accepted_rows'],r['eligible_orders']+r['excluded_accepted_rows'])
    def test_gate_failure_preserves_previous_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            data,out,site=self.setup_data(d);run(data,out,site,ROOT/'sql/monthly_sales.sql',self.as_of)
            before=(out/'run.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'Quality gate failed'):run(data,out,site,ROOT/'sql/monthly_sales.sql',self.as_of,0)
            self.assertEqual(before,(out/'run.json').read_bytes())
    def test_sql_reconciliation_failure_preserves_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            data,out,site=self.setup_data(d);run(data,out,site,ROOT/'sql/monthly_sales.sql',self.as_of)
            before=(out/'run.json').read_bytes();bad=Path(d)/'bad.sql'
            bad.write_text("SELECT '2026-10' AS month,1 AS orders,1 AS gross_cents,0 AS refund_cents,1 AS net_cents")
            with self.assertRaisesRegex(ValueError,'Reconciliation failed'):run(data,out,site,bad,self.as_of)
            self.assertEqual(before,(out/'run.json').read_bytes())
    def test_monthly_control_detects_wrong_month_with_same_grand_total(self):
        with tempfile.TemporaryDirectory() as d:
            data,out,site=self.setup_data(d)
            sql=Path(d)/'wrong_month.sql'
            sql.write_text((ROOT/'sql/monthly_sales.sql').read_text().replace('SELECT substr(order_date, 1, 7) AS month', "SELECT '1900-01' AS month"))
            with self.assertRaisesRegex(ValueError,'Reconciliation failed'):run(data,out,site,sql,self.as_of)
    def test_threshold_boundary_is_inclusive(self):
        with tempfile.TemporaryDirectory() as d:
            data,out,site=self.setup_data(d)
            r=run(data,out,site,ROOT/'sql/monthly_sales.sql',self.as_of,6/405)
            self.assertEqual(r['accepted_rows'],399)
    def test_rerun_has_no_duplicate_loads_and_identical_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            data,out,site=self.setup_data(d);a=run(data,out,site,ROOT/'sql/monthly_sales.sql',self.as_of)
            files={p.name:p.read_bytes() for p in out.iterdir() if p.suffix!='.sqlite'}
            b=run(data,out,site,ROOT/'sql/monthly_sales.sql',self.as_of)
            self.assertEqual(a,b);self.assertEqual(files,{p.name:p.read_bytes() for p in out.iterdir() if p.suffix!='.sqlite'})
    def test_cancellation_and_full_refund_are_not_quality_rejects(self):
        a,r=validate(CUSTOMERS,[row(status='cancelled'),row(order_id='O2',refund_eur='10')],self.as_of)
        self.assertEqual(len(a),2);self.assertEqual(r,[])
    def test_invalid_threshold(self):
        with tempfile.TemporaryDirectory() as d:
            data,out,site=self.setup_data(d)
            for threshold in [-1,2,float('nan')]:
                with self.assertRaises(ValueError):run(data,out,site,ROOT/'sql/monthly_sales.sql',self.as_of,threshold)
if __name__=='__main__':unittest.main()
