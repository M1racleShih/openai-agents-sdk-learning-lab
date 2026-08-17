"""Contracts for the evidence worker."""

from pydantic import BaseModel


class TaskRequest(BaseModel):
    task_id: str
    question: str
    requested_source_ids: list[str]


class Evidence(BaseModel):
    source_id: str
    summary: str


class WorkerError(BaseModel):
    code: str
    message: str


class WorkerResult(BaseModel):
    task_id: str
    answer: str
    evidence: list[Evidence]
    errors: list[WorkerError]
