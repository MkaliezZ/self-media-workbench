"""Explicit, source-bound 2D visual plans for the calling Agent."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

WordID = Annotated[int, Field(ge=0)]
Colour = Annotated[str, Field(pattern=r'^[0-9A-Fa-f]{6}$')]


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Rect(Strict):
    x: float = Field(ge=0, le=1, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, allow_inf_nan=False)
    width: float = Field(gt=0, le=1, allow_inf_nan=False)
    height: float = Field(gt=0, le=1, allow_inf_nan=False)

    @model_validator(mode='after')
    def bounds(self):
        if self.x+self.width>1.000001 or self.y+self.height>1.000001:
            raise ValueError('Rectangle must stay inside its normalized coordinate space')
        return self


class Mark(Strict):
    word_ids: list[WordID] = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1000)


class Region(Mark):
    rect: Rect
    colour: Colour = 'FFD54F'


class ImageCue(Mark):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    nature: Literal['unknown','recorded','generated','illustration','mixed'] = 'unknown'
    source_note: str = Field(min_length=1, max_length=2000)
    usage_scope: str = Field(min_length=1, max_length=2000)
    slot: Rect = Field(description='Normalized destination rectangle. Image fits inside without cropping.')
    highlight: Rect | None = Field(default=None, description='Optional rectangle in original image coordinates, normalized before contain-fit.')


class CaptionStyle(Strict):
    enabled: bool = True
    font_height: float = Field(default=.05, ge=.02, le=.10, allow_inf_nan=False)
    bottom_margin: float = Field(default=.08, ge=.02, le=.35, allow_inf_nan=False)
    colour: Colour = 'FFFFFF'
    emphasis_colour: Colour = 'FFD54F'
    font_path: str | None = None


class TemplateBinding(Strict):
    id: str = Field(pattern=r'^[a-z_]{1,60}$')
    version: str
    definition_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    compiler_version: str
    selection_reason: str = Field(min_length=1,max_length=2000)
    beats: list[dict] = Field(min_length=1,max_length=32)
    frame_inspection_note: str = Field(min_length=1,max_length=2000)
    protected_regions: list[Rect] = Field(default_factory=list,max_length=32)
    custom_definition: dict | None = None


class VisualPlan(Strict):
    request_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    project_revision: int = Field(ge=1)
    review_revision: int = Field(ge=0)
    asr_run: str = Field(min_length=1, max_length=80)
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    reason: str = Field(min_length=1, max_length=2000)
    template: TemplateBinding | None = None
    captions: CaptionStyle = Field(default_factory=CaptionStyle)
    emphasis: list[Mark] = Field(default_factory=list, max_length=64,
        description='Each selection must equal one reviewed caption group. Highlights that complete cue, not invented character timing.')
    images: list[ImageCue] = Field(default_factory=list, max_length=8)
    regions: list[Region] = Field(default_factory=list, max_length=32,
        description='Static rectangles in normalized video coordinates. No object tracking.')
