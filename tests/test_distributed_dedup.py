import json
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("ray")


def test_run_distributed_cli(tmp_path):
    data = tmp_path / "data.jsonl"
    data.write_text('{"text":"a"}\n{"text":"a"}\n', encoding="utf-8")
    out = tmp_path / "out.jsonl"
    log_csv = tmp_path / "log.csv"
    cand = tmp_path / "cand.json"
    conf = tmp_path / "conf.yaml"
    conf.write_text("redis:\n  host: localhost\n  port: 6379\n", encoding="utf-8")

    cmd = [
        "python",
        "-m",
        "dedup.distributed_dedup",
        "--input",
        str(data),
        "--output",
        str(out),
        "--log-csv",
        str(log_csv),
        "--candidates",
        str(cand),
        "--config",
        str(conf),
        "--num-workers",
        "1",
        "--chunk-size",
        "1",
        "--local",
    ]

    subprocess.run(cmd, check=True)

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) <= 2
    assert log_csv.exists()
    assert cand.exists()
