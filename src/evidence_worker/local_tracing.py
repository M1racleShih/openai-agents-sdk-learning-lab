"""Configure local-only tracing for the learning exercises."""

from __future__ import annotations

from pathlib import Path

import mlflow
import mlflow.openai as mlflow_openai
from agents import set_trace_processors

DEFAULT_MLFLOW_DIR = Path(__file__).resolve().parents[2] / ".mlflow"
DEFAULT_EXPERIMENT_NAME = "agents-sdk-learning-lab"


def configure_local_tracing(storage_dir: Path = DEFAULT_MLFLOW_DIR) -> None:
    """Replace the OpenAI exporter with MLflow backed by a local SQLite file."""
    storage_dir.mkdir(parents=True, exist_ok=True)

    database_uri = f"sqlite:///{(storage_dir / 'mlflow.db').as_posix()}"
    artifact_uri = (storage_dir / "artifacts").resolve().as_uri()

    # Remove the SDK processor that uploads to api.openai.com before installing
    # the MLflow processor. Model calls keep using their independently configured client.
    set_trace_processors([])
    mlflow.set_tracking_uri(database_uri)
    if mlflow.get_experiment_by_name(DEFAULT_EXPERIMENT_NAME) is None:
        mlflow.create_experiment(DEFAULT_EXPERIMENT_NAME, artifact_location=artifact_uri)
    mlflow.set_experiment(DEFAULT_EXPERIMENT_NAME)
    mlflow_openai.autolog(disable_openai_agent_tracer=True)
