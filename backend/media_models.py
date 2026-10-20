"""Agent-discoverable review edit contract; align to real ASR groups, never chars."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MediaImport(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    path: str = Field(min_length=1, description='Existing local absolute audio/video path; copied as immutable original. Network shares are not accepted.')
    media_nature: Literal['unknown', 'recorded', 'generated', 'restored', 'mixed'] = 'unknown'
    source_note: str = Field(default='', max_length=2000)
    usage_scope: str = Field(default='', max_length=2000)


class SpeechCut(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str = Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    word_ids: list[Annotated[int, Field(ge=0)]] = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)
    kind: Literal['mistake', 'repetition', 'retake', 'filler', 'other']
    start: float | None = Field(default=None, ge=0, allow_inf_nan=False,
                               description='Optional original-source cut start; must include every selected group completely.')
    end: float | None = Field(default=None, gt=0, allow_inf_nan=False,
                             description='Provide both start/end, or neither to use selected group bounds. Cannot touch an unselected group.')

    @model_validator(mode='after')
    def boundaries(self):
        if not self.reason.strip():
            raise ValueError('有声删除须说明实际理由')
        if (self.start is None) != (self.end is None):
            raise ValueError('有声删除的start/end须同时提供或同时省略')
        return self


class ReviewEdit(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    revision: int = Field(ge=0)
    asr_run: str | None = Field(default=None, min_length=1, max_length=80)
    source_sha256: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    corrections: dict[str, str] = Field(default_factory=dict)
    selected_ids: list[str] | None = Field(default=None,
                                         description='Selected pause IDs; omitted preserves selection, [] restores all pauses.')
    speech_cuts: list[SpeechCut] | None = Field(default=None,
                                              description='Explicit full replacement of spoken-cut decisions; omitted preserves them, [] restores spoken groups. Requires asr_run/source_sha256.')
    caption_groups: list[list[Annotated[int, Field(ge=0)]]] | None = Field(default=None,
        description='Optional SRT grouping using ASR word IDs. Nonempty groups must cover all retained groups exactly once in source order; no audio/time edits. Omitted preserves grouping; [] resets automatic grouping. Requires source/run binding.')

    @model_validator(mode='after')
    def source_binding(self):
        if (self.speech_cuts is not None or self.caption_groups is not None) and (not self.asr_run or not self.source_sha256):
            raise ValueError('提交或撤回有声删除/字幕分组须绑定asr_run和source_sha256')
        return self


class ExportReview(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    revision: int = Field(ge=0)
    asr_run: str = Field(min_length=1, max_length=80)
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
