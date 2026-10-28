"""Lighting planning inputs: declarations, calibrated data and unknowns stay distinct."""
import math
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class Point(Strict):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class Obstacle(Strict):
    label: str = Field(min_length=1, max_length=100)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    depth: float = Field(gt=0, le=1)
    height_m: float | None = Field(default=None, gt=0, le=8)
    blocks_light: bool = True

    @model_validator(mode='after')
    def inside(self):
        if self.x+self.width > 1.000001 or self.y+self.depth > 1.000001:
            raise ValueError('Obstacle must stay inside the scene')
        return self


class Window(Strict):
    label: str = Field(default='窗户', max_length=100)
    point: Point
    usable: bool = False
    note: str = Field(default='', max_length=500)


class Observation(Strict):
    image_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    note: str = Field(min_length=1, max_length=2000)


class Photometry(Strict):
    reference_lux: float = Field(gt=0, le=10000000)
    reference_distance_m: float = Field(gt=0, le=100)
    modifier: str = Field(min_length=1, max_length=200)
    cct_k: int = Field(ge=1800, le=12000)
    source: str = Field(min_length=1, max_length=1000)
    measured_at: str = Field(min_length=1, max_length=100)
    basis: Literal['manufacturer', 'user_measurement']
    minimum_distance_m: float = Field(default=1.0, ge=.05, le=100)
    # Only matching assembly/CCT at full output; no assumed dimmer curve.


class Fixture(Strict):
    label: str = Field(min_length=1, max_length=200)
    input_watts: float | None = Field(default=None, gt=0, le=3000)
    modifier: str = Field(default='柔光箱，规格待核对', min_length=1, max_length=200)
    cct_k: int = Field(default=5600, ge=1800, le=12000)
    photometry: Photometry | None = None

    @model_validator(mode='after')
    def matching_assembly(self):
        if self.photometry and (self.modifier != self.photometry.modifier or self.cct_k != self.photometry.cct_k):
            raise ValueError('Photometry must match the exact modifier and color temperature')
        return self


class Scene(Strict):
    image_ids: list[str] = Field(default_factory=list, max_length=8)
    assessment: Literal['assumed', 'user_confirmed', 'agent_reviewed'] = 'assumed'
    observations: list[Observation] = Field(default_factory=list, max_length=20)
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    purpose: str = Field(default='单人固定机位口播', min_length=1, max_length=200)
    width_m: float | None = Field(default=None, ge=.6, le=30)
    depth_m: float | None = Field(default=None, ge=.6, le=30)
    ceiling_m: float | None = Field(default=None, ge=1.8, le=8)
    face_height_m: float | None = Field(default=None, ge=.5, le=2.5)
    subject: Point = Field(default_factory=lambda: Point(x=.5, y=.45))
    camera: Point = Field(default_factory=lambda: Point(x=.5, y=.88))
    windows: list[Window] = Field(default_factory=list, max_length=8)
    obstacles: list[Obstacle] = Field(default_factory=list, max_length=24)
    fixtures: list[Fixture] = Field(default_factory=list, max_length=8)
    key_side: Literal['auto', 'left', 'right'] = 'auto'
    look: Literal['natural', 'contrast'] = 'natural'
    glasses: bool = False
    target_lux: float | None = Field(default=None, gt=0, le=100000)

    @model_validator(mode='after')
    def consistent(self):
        if (self.width_m is None) != (self.depth_m is None):
            raise ValueError('Room width and depth must be supplied together')
        if self.face_height_m and self.ceiling_m and self.face_height_m >= self.ceiling_m:
            raise ValueError('Face height must be below the ceiling')
        if math.hypot(self.camera.x-self.subject.x, self.camera.y-self.subject.y) < .05:
            raise ValueError('Camera and subject need distinct positions')
        if len(set(self.image_ids)) != len(self.image_ids):
            raise ValueError('Duplicate image IDs')
        if self.assessment == 'agent_reviewed' and not self.observations:
            raise ValueError('Agent review needs image-bound observations')
        if any(o.image_id not in self.image_ids for o in self.observations):
            raise ValueError('Observations must reference the bound images')
        for p in (self.subject,self.camera):
            if any(o.x < p.x < o.x+o.width and o.y < p.y < o.y+o.depth for o in self.obstacles):
                raise ValueError('Subject/camera cannot be inside a no-placement obstacle')
        return self


class Generate(Strict):
    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex, pattern=r'^[A-Za-z0-9_-]{1,80}$')
    project_revision: int = Field(ge=1)
    supersedes: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    revision_reason: str = Field(default='首次生成三档布光初稿', min_length=1, max_length=2000)
    scene: Scene


class Selection(Strict):
    project_revision: int = Field(ge=1)
    tier: Literal['simple', 'standard', 'ideal']


class FieldCheck(Strict):
    project_revision: int = Field(ge=1)
    tier: Literal['simple', 'standard', 'ideal']
    image_ids: list[str] = Field(default_factory=list, max_length=8)
    note: str = Field(min_length=1, max_length=2000)
    next_adjustment: str = Field(min_length=1, max_length=1000)
    exposure_note: str = Field(default='', max_length=1000)
    measured_lux: float | None = Field(default=None, ge=0, le=10000000)
    measurement_point: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def measured(self):
        if self.measured_lux is not None and not self.measurement_point.strip():
            raise ValueError('Measured lux needs the actual point and sensor orientation')
        return self
