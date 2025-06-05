import os
import sys
import subprocess
from pathlib import Path
import pytest

pytest.importorskip("torch")
pytest.importorskip("datasketch")
pytest.importorskip("pyarrow")


def _make_fake_python(tmp: Path) -> Path:
    """Return path to a fake python executable that mocks pipeline modules."""
    script = tmp / "python"
    script.write_text(
        """#!/usr/bin/env python3
import os, sys
from pathlib import Path
args = sys.argv[1:]
if args and args[0] == '-m':
    mod = args[1]
    if mod == 'dedup.slimpajama_dedup':
        out = Path(args[args.index('--output') + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text('{}\n')
    elif mod == 'format.to_parquet':
        out = Path(args[args.index('--output') + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b'PARQUET')
    elif mod == 'dem.train_individual':
        out_dir = Path(args[args.index('--output-dir') + 1])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'adapter_model.bin').write_bytes(b'lora')
    elif mod == 'dem.vector_diff':
        idx_lora = args.index('--lora-dirs')
        idx_out = args.index('--output-dir')
        loras = args[idx_lora + 1:idx_out]
        out_dir = Path(args[idx_out + 1])
        out_dir.mkdir(parents=True, exist_ok=True)
        for ld in loras:
            domain = Path(ld).name.replace('lora_', '')
            (out_dir / f'{domain}.pt').write_bytes(b'diff')
    elif mod == 'dem.merge_model':
        out_dir = Path(args[args.index('--output-dir') + 1])
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'pytorch_model.bin').write_bytes(b'model')
    elif mod == 'evaluation.eval_runner':
        out = Path(args[args.index('--output') + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text('{}')
        md = Path(args[args.index('--md-output') + 1])
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text('# md')
    elif mod == 'evaluation.compute_metrics':
        out = Path(args[args.index('--output') + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text('metric')
    else:
        pass
    sys.exit(0)
os.execvp(sys.executable, [sys.executable] + sys.argv[1:])
"""
    )
    script.chmod(0o755)
    return script


def test_run_pipeline_script(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "run_pipeline.sh"

    input1 = tmp_path / "domain1.jsonl"
    input1.write_text('{"text":"a"}\n', encoding="utf-8")
    input2 = tmp_path / "domain2.jsonl"
    input2.write_text('{"text":"b"}\n', encoding="utf-8")

    fake_python = _make_fake_python(tmp_path)
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"

    subprocess.run(
        ["bash", str(script), str(input1), str(input2)], cwd=repo, env=env, check=True
    )

    dedup1 = repo / "data" / "deduped" / "domain1_deduped.jsonl"
    parquet1 = repo / "data" / "parquet" / "domain1_deduped.parquet"
    lora1 = repo / "models" / "lora_domain1" / "adapter_model.bin"
    merged = repo / "models" / "merged" / "pytorch_model.bin"

    assert dedup1.exists()
    assert parquet1.exists()
    assert lora1.exists()
    assert merged.exists()

    for path in ["data", "models", "logs", "results", "eval"]:
        target = repo / path
        if target.exists():
            import shutil

            shutil.rmtree(target)
