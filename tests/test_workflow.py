import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import io,json,tempfile,unittest,zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
runner=load('runner',ROOT/'run_agents.py')
repro=load('repro',ROOT/'scripts/reproduce.py')

class Transfer:
    def __init__(self,body):self.body=body
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def stream_to_file(self,path):Path(path).write_bytes(self.body)

class WorkflowTests(unittest.TestCase):
    def test_money_weighted_cashflows(self):
        self.assertAlmostEqual(repro.annual_return(['2020-01-01'],[1000],'2021-01-01',1100,basis=366),.1,places=12)
        self.assertAlmostEqual(repro.annual_return(['2020-01-01','2020-07-01'],[1000,1000],'2021-01-01',2000),0,places=12)

    def test_download_path_boundaries(self):
        with tempfile.TemporaryDirectory() as td:
            for bad in ['/etc/passwd','/workspace/outputs/../secret','relative.csv','/workspace/outputs/a\\b']:
                with self.assertRaises(ValueError):runner.safe_destination(td,bad)
            self.assertEqual(runner.safe_destination(td,'/workspace/outputs/data/a.csv'),Path(td).resolve()/'data/a.csv')
            (Path(td)/'escape').symlink_to(Path(td).parent,target_is_directory=True)
            with self.assertRaises(ValueError):runner.safe_destination(td,'/workspace/outputs/escape/a.csv')

    def test_downloads_real_bytes_and_filters_turns(self):
        zipped=io.BytesIO()
        with zipfile.ZipFile(zipped,'w') as z:z.writestr('result.txt','verified transfer fixture')
        payloads={n:(b'{}' if n=='audit.json' else zipped.getvalue() if n.endswith('.zip') else b'fixture\n') for n in runner.REQUIRED}
        artifacts=[NS(id=n,path='/workspace/outputs/'+n,turn_id='turn_good') for n in payloads]
        artifacts.append(NS(id='old',path='/workspace/outputs/old.txt',turn_id='turn_old'))
        api=NS(list=lambda *args,**kwargs:iter(artifacts),with_streaming_response=NS(content=lambda id,**kwargs:Transfer(payloads[id])))
        client=NS(beta=NS(agents=NS(sessions=NS(artifacts=api))))
        with tempfile.TemporaryDirectory() as td:
            manifest=runner.download_artifacts(client,'sess_test','turn_good',td)
            self.assertEqual(len(manifest),len(runner.REQUIRED))
            self.assertFalse((Path(td)/'old.txt').exists())
            self.assertEqual((Path(td)/'research_bundle.zip').read_bytes(),zipped.getvalue())
            self.assertEqual(len(json.loads((Path(td)/'download_manifest.json').read_text())),len(runner.REQUIRED))

    def test_missing_outputs_is_failure(self):
        api=NS(list=lambda *args,**kwargs:[])
        client=NS(beta=NS(agents=NS(sessions=NS(artifacts=api))))
        with tempfile.TemporaryDirectory() as td,patch.object(runner.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'did not publish'):runner.download_artifacts(client,'s','t',td)

    def test_complete_universe_mode_refuses_missing_data(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,'235/499 candidates missing'):
                repro.run(ROOT/'data/Backtest_Data_and_Code.zip',Path(td)/'result')
            self.assertFalse((Path(td)/'result').exists())

if __name__=='__main__':unittest.main()
