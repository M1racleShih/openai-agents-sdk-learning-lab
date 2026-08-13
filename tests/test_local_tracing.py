from pathlib import Path

from evidence_worker import local_tracing


def test_local_tracing_replaces_openai_exporter_and_uses_local_storage(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        local_tracing,
        "set_trace_processors",
        lambda processors: calls.append(("processors", processors)),
    )
    monkeypatch.setattr(
        local_tracing.mlflow,
        "set_tracking_uri",
        lambda uri: calls.append(("tracking_uri", uri)),
    )
    monkeypatch.setattr(
        local_tracing.mlflow,
        "get_experiment_by_name",
        lambda name: None,
    )
    monkeypatch.setattr(
        local_tracing.mlflow,
        "create_experiment",
        lambda name, artifact_location: calls.append(
            ("create_experiment", (name, artifact_location))
        ),
    )
    monkeypatch.setattr(
        local_tracing.mlflow,
        "set_experiment",
        lambda name: calls.append(("set_experiment", name)),
    )
    monkeypatch.setattr(
        local_tracing.mlflow_openai,
        "autolog",
        lambda **kwargs: calls.append(("autolog", kwargs)),
    )

    local_tracing.configure_local_tracing(tmp_path)

    assert calls == [
        ("processors", []),
        ("tracking_uri", f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"),
        (
            "create_experiment",
            (
                "agents-sdk-learning-lab",
                (tmp_path / "artifacts").resolve().as_uri(),
            ),
        ),
        ("set_experiment", "agents-sdk-learning-lab"),
        ("autolog", {"disable_openai_agent_tracer": True}),
    ]
