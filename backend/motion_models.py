"""Source-bound, authored motion effects; no automatic OCR/tracking claims."""
from typing import Annotated,Literal,Union
from pydantic import Field,model_validator
from visual_models import Strict,Rect,Colour


class Timed(Strict):
    start: float=Field(ge=0,allow_inf_nan=False)
    end: float=Field(gt=0,allow_inf_nan=False)
    reason: str=Field(min_length=1,max_length=1000)


class Point(Strict):
    x: float=Field(ge=0,le=1,allow_inf_nan=False)
    y: float=Field(ge=0,le=1,allow_inf_nan=False)


class DocumentExtract(Timed):
    kind: Literal['document_extract']
    source_id: str
    source_rect: Rect
    highlights: list[Rect]=Field(min_length=1,max_length=12,description='Actual source-image line rectangles, not invented OCR geometry')
    page_quad: list[Point]=Field(min_length=4,max_length=4,description='Clockwise TL/TR/BR/BL in output coordinates')
    target_rect: Rect
    quote: str=Field(min_length=1,max_length=1000,description='Caller-reviewed transcription; crop pixels remain authoritative, no OCR certification')
    reveal_seconds: float=Field(default=.4,ge=0,le=3,allow_inf_nan=False)
    highlight_seconds: float=Field(default=.8,gt=0,le=5,allow_inf_nan=False)
    lift_seconds: float=Field(default=.8,gt=0,le=5,allow_inf_nan=False)
    return_seconds: float=Field(default=.8,gt=0,le=5,allow_inf_nan=False)
    dim: float=Field(default=.6,ge=0,le=.95,allow_inf_nan=False)
    colour: Colour='FFE66B'


class MotionLayer(Timed):
    kind: Literal['motion_layer']
    source_id: str
    source_in: float=Field(default=0.,ge=0,allow_inf_nan=False)
    crop: Rect=Field(default_factory=lambda:Rect(x=0.,y=0.,width=1.,height=1.))
    from_rect: Rect
    to_rect: Rect
    enter_seconds: float=Field(default=.8,gt=0,le=5,allow_inf_nan=False)
    exit_seconds: float=Field(default=.5,ge=0,le=5,allow_inf_nan=False)
    animation: Literal['move','pop','reveal_left','reveal_up']='move'
    easing: Literal['smoothstep','ease_out_cubic']='smoothstep'
    from_angle: float=Field(default=0.,ge=-30,le=30,allow_inf_nan=False)
    to_angle: float=Field(default=0.,ge=-30,le=30,allow_inf_nan=False)
    shape: Literal['rectangle','ellipse']='rectangle'
    feather: int=Field(default=0,ge=0,le=64)
    opacity: float=Field(default=1.,gt=0,le=1,allow_inf_nan=False)
    dim: float=Field(default=0.,ge=0,le=.95,allow_inf_nan=False)
    shadow: bool=True


class Spotlight(Timed):
    kind: Literal['spotlight']
    from_rect: Rect
    to_rect: Rect
    shape: Literal['rectangle','ellipse']='rectangle'
    feather: int=Field(default=20,ge=0,le=64)
    dim: float=Field(default=.72,gt=0,le=.95,allow_inf_nan=False)
    fade_seconds: float=Field(default=.4,gt=0,le=3,allow_inf_nan=False)
    colour: Colour='FFD66B'


class MotionText(Timed):
    kind: Literal['motion_text']
    text: str=Field(min_length=1,max_length=160)
    accent: str=Field(default='',max_length=80)
    slot: Rect
    font_height: float=Field(default=.075,ge=.025,le=.16,allow_inf_nan=False)
    colour: Colour='FFFFFF'
    accent_colour: Colour='FFD66B'
    animation: Literal['slide_up','pop','fade']='slide_up'
    enter_seconds: float=Field(default=.6,gt=0,le=4,allow_inf_nan=False)
    exit_seconds: float=Field(default=.4,ge=0,le=4,allow_inf_nan=False)


class TrackMatte(MotionLayer):
    kind: Literal['track_matte']
    matte_id: str=Field(min_length=1)
    matte_mode: Literal['alpha','luma']='alpha'
    invert: bool=False


Effect=Annotated[Union[DocumentExtract,MotionLayer,Spotlight,MotionText,TrackMatte],Field(discriminator='kind')]
