"""Build the downloadable research archive, excluding secrets and temporary files."""
from pathlib import Path
import hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','.venv','__pycache__','agent_downloads','reproduced','media'}
def include(p):
    rel=p.relative_to(ROOT)
    return p.is_file() and not any(x in SKIP for x in rel.parts) and p.name not in {
        'research_bundle.zip','make_video.py','SHA256SUMS.json','.agent-state.json','.agent-state.tmp','.DS_Store'
    } and not p.name.endswith('.pyc') and (not p.name.startswith('.env') or p.name=='.env.example')

files=sorted(p for p in ROOT.rglob('*') if include(p))
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
manifest_path=ROOT/'data/SHA256SUMS.json';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(ROOT/'research_bundle.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files+[manifest_path]:z.write(p,str(Path('monthly-winner-research')/p.relative_to(ROOT)))
with zipfile.ZipFile(ROOT/'research_bundle.zip') as z:
    assert z.testzip() is None
    assert not any(n.endswith('/.env') or '/.git/' in n for n in z.namelist())
print(f'Packaged {len(files)+1} files: {ROOT / "research_bundle.zip"}')
