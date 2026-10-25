"""Native source-time timeline, independent of ASR and subtitle grouping."""
from typing import Literal
from pydantic import Field,model_validator
from visual_models import Strict,Colour,Rect
from editing_templates import RecipeDefinition


class SourceRef(Strict):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    kind: Literal['media','image']='media'
    asset_id: str = Field(min_length=1,max_length=80)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


class Shot(Strict):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    source_id: str
    source_in: float = Field(ge=0,allow_inf_nan=False)
    source_out: float = Field(gt=0,allow_inf_nan=False)
    role: str = Field(min_length=1,max_length=200)
    reason: str = Field(min_length=1,max_length=2000)
    fit: Literal['contain','cover']='contain'
    source_audio_gain: float = Field(default=1.,ge=0,le=4,allow_inf_nan=False)


class AudioBed(Strict):
    source_id: str
    role: Literal['music','ambient','voice','effect']
    source_in: float = Field(default=0.,ge=0,allow_inf_nan=False)
    start: float = Field(default=0.,ge=0,allow_inf_nan=False)
    duration: float = Field(gt=0,allow_inf_nan=False)
    gain: float = Field(default=.3,ge=0,le=4,allow_inf_nan=False)
    fade_in: float = Field(default=0.,ge=0,allow_inf_nan=False)
    fade_out: float = Field(default=0.,ge=0,allow_inf_nan=False)
    reason: str = Field(min_length=1,max_length=2000)


class MusicGrid(Strict):
    source_id: str
    source_times: list[float] = Field(min_length=2,max_length=129,
        description='Reviewed music-source times, one for each shot edge including opening and ending.')
    method: Literal['manual','reviewed_onsets']
    reason: str = Field(min_length=1,max_length=2000)
    max_error_frames: int = Field(default=1,ge=0,le=2)


class Title(Strict):
    text: str = Field(min_length=1,max_length=160)
    start: float = Field(ge=0,allow_inf_nan=False)
    end: float = Field(gt=0,allow_inf_nan=False)
    colour: Colour='FFFFFF'
    font_height: float = Field(default=.05,ge=.02,le=.1,allow_inf_nan=False)
    bottom_margin: float = Field(default=.08,ge=.02,le=.35,allow_inf_nan=False)


class Transition(Strict):
    after_shot_id: str
    kind: Literal['fade','wipeleft','wiperight','slideleft','slideright','circleopen']
    duration: float = Field(ge=.08,le=2,allow_inf_nan=False)
    reason: str = Field(min_length=1,max_length=1000)


class MaskCue(Strict):
    source_id: str
    source_in: float = Field(default=0.,ge=0,allow_inf_nan=False)
    start: float = Field(ge=0,allow_inf_nan=False)
    end: float = Field(gt=0,allow_inf_nan=False)
    crop: Rect = Field(default_factory=lambda:Rect(x=0.,y=0.,width=1.,height=1.))
    slot: Rect
    shape: Literal['rectangle','ellipse']='ellipse'
    feather: int = Field(default=12,ge=0,le=64)
    opacity: float = Field(default=1.,gt=0,le=1,allow_inf_nan=False)
    reason: str = Field(min_length=1,max_length=1000)


class TimelinePlan(Strict):
    request_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    project_revision: int = Field(ge=1)
    supersedes: str | None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    revision_reason: str = Field(min_length=1,max_length=2000)
    intent: str = Field(min_length=1,max_length=2000)
    logic_id: str | None = None
    recipe: RecipeDefinition | None=None
    width: int = Field(default=1280,ge=160,le=3840)
    height: int = Field(default=720,ge=160,le=3840)
    fps: int = Field(default=25,ge=15,le=60)
    sources: list[SourceRef] = Field(min_length=1,max_length=128)
    shots: list[Shot] = Field(min_length=1,max_length=128)
    audio: list[AudioBed] = Field(default_factory=list,max_length=16)
    music_grid: MusicGrid | None=None
    titles: list[Title] = Field(default_factory=list,max_length=64)
    transitions: list[Transition] = Field(default_factory=list,max_length=31)
    masks: list[MaskCue] = Field(default_factory=list,max_length=16)
    font_path: str | None=None

    @model_validator(mode='after')
    def coherent(self):
        if self.width%2 or self.height%2:raise ValueError('Canvas dimensions must be even')
        for key in ('sources','shots'):
            ids=[v.id for v in getattr(self,key)]
            if len(ids)!=len(set(ids)):raise ValueError('Source and shot IDs must be unique')
        if not self.intent.strip() or not self.revision_reason.strip():raise ValueError('Explain the editing goal and revision')
        if self.recipe:
            if self.recipe.execution_mode!='native_timeline':raise ValueError('Native timeline recipes must declare native_timeline mode')
            roles=[r.id for r in self.recipe.roles];actual=[s.role for s in self.shots]
            if any(r not in roles for r in actual) or set(actual)!=set(roles) or [roles.index(r) for r in actual]!=sorted(roles.index(r) for r in actual):
                raise ValueError('Shots must cover the native recipe roles in the declared narrative order')
        return self


class TimelineExport(Strict):
    plan_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class OnsetRequest(Strict):
    media_id: str
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    source_in: float = Field(default=0.,ge=0,allow_inf_nan=False)
    source_out: float = Field(gt=0,allow_inf_nan=False)
