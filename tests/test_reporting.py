from pathlib import Path

from chat_analyzer.reporting import write_reports


def test_write_reports_html_json_md(tmp_path: Path):
    chart_file = tmp_path / "chart.html"
    chart_file.write_text('<div class="plotly-graph-div"></div>', encoding="utf-8")

    written = write_reports(
        output_dir=str(tmp_path),
        report_format="all",
        summary={"total_messages": 10, "participants": 2, "start": "2026-01-01", "end": "2026-01-02", "timezone": "UTC"},
        module_results={"summary": {"metrics": {"total_messages": 10}, "artifacts": {}, "warnings": []}},
        chart_paths={"sample": {"html_path": str(chart_file), "png_path": None}},
        extra_artifacts={"social_graph": str(tmp_path / "social_graph.html")},
        insights_top=5,
    )

    assert {"html", "md", "json"}.issubset(written.keys())
    html = Path(written["html"]).read_text(encoding="utf-8")
    assert "plotly-graph-div" in html
