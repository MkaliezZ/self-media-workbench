"""Version 1 agent artifacts. Schemas describe structure, not truth."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Link(Record):
    source_id: str
    quote: str = Field(min_length=1)


class Claim(Record):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    kind: Literal['observation', 'hypothesis', 'plan', 'fictional']
    evidence: list[Link]
    limitation: str


class Diagnosis(Record):
    objective: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    account_scope: str = Field(min_length=1)
    claims: list[Claim] = Field(min_length=1)
    priority_action: str = Field(min_length=1)


class Topic(Record):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    claim_ids: list[str] = Field(min_length=1)


class Topics(Record):
    claims: list[Claim] = Field(min_length=1)
    candidates: list[Topic] = Field(min_length=1)
    selected_id: str
    selection_reason: str = Field(min_length=1)


class Segment(Record):
    id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    spoken: str = Field(min_length=1)
    visual: str = Field(min_length=1)
    subtitle: str
    claim_ids: list[str] = Field(min_length=1)


class Script(Record):
    topic_artifact_id: str | None
    topic_id: str | None
    claims: list[Claim] = Field(min_length=1)
    segments: list[Segment] = Field(min_length=1)
    cta: str
    production_limits: list[str]


class Asset(Record):
    media_id: str
    export_id: str | None


class Check(Record):
    item: str = Field(min_length=1)
    state: Literal['checked', 'missing', 'not_applicable']
    evidence: list[Link]


class Publish(Record):
    script_artifact_id: str | None
    title: str = Field(min_length=1)
    caption: str
    disclosure: str
    assets: list[Asset]
    checklist: list[Check] = Field(min_length=1)


class Metric(Record):
    name: str = Field(min_length=1)
    numerator: float | None = Field(ge=0)
    denominator: float | None = Field(ge=0)
    value: float | None
    unit: Literal['ratio', 'percent', 'count', 'seconds']
    window: str = Field(min_length=1)
    collected_at: str | None
    evidence: list[Link]


class Experiment(Record):
    variable: str = Field(min_length=1)
    change: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    stop_rule: str = Field(min_length=1)


class Review(Record):
    publish_artifact_id: str | None
    observation_type: Literal['planned', 'simulated', 'published']
    claims: list[Claim] = Field(min_length=1)
    metrics: list[Metric]
    hypotheses: list[str]
    next_experiment: Experiment


class Submission(Record):
    request_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    revision: int = Field(ge=1)
    context_id: str
    stage: Literal['diagnose', 'topics', 'script', 'publish', 'review']
    input_artifact_ids: list[str]
    standalone_reason: str | None
    payload: dict
    declared_status: Literal['needs_review', 'ready_for_recording', 'ready_to_publish',
                             'published_observed', 'simulation_pass']
    unresolved: list[str]
    supersedes: str | None
    revision_reason: str | None


class Source(Record):
    revision: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=200)
    nature: Literal['provided', 'observed', 'simulation', 'reference']
    origin: str = Field(min_length=1, max_length=2000)
    content: str = Field(min_length=1, max_length=1000000)


MODELS = {'diagnose':Diagnosis, 'topics':Topics, 'script':Script,
          'publish':Publish, 'review':Review}
