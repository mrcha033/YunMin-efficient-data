import json
from pathlib import Path
import pytest
pytest.importorskip("datasketch")

from dedup.mapreduce_dedup_driver import run_dedup_mapreduce


def test_run_mapreduce(tmp_path):
    data = tmp_path / "data.jsonl"
    data.write_text('{"text":"a"}\n{"text":"a"}\n', encoding="utf-8")
    out = tmp_path / "out.jsonl"
    conf = tmp_path / "conf.yaml"
    conf.write_text("redis:\n  host: localhost\n  port: 6379\n", encoding="utf-8")
    run_dedup_mapreduce(str(data), str(out), str(conf), workers=1, chunk_size=1)
    lines = out.read_text(encoding="utf-8").strip().split('\n')
    assert len(lines) <= 2
