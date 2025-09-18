from pathlib import Path

import pandas as pd

from trade_app.adapters.results.file_results_sink import FileResultsSinkAdapter


def test_file_results_sink_writes_parquet_csv_json(tmp_path: Path):
    table = pd.DataFrame(
        {
            "oos_start": ["2024-01-01"],
            "oos_end": ["2024-01-02"],
            "total_return": [0.1],
        }
    )
    summary = {"folds": 1, "mean": {"total_return": 0.1}}

    sink = FileResultsSinkAdapter()
    paths = sink.write(table, summary, base_dir=tmp_path, experiment_name="exp1", fmt="both")

    assert paths["folds_parquet"].exists()
    assert paths["folds_csv"].exists()
    assert paths["summary_json"].exists()
