"""Bounded parameters for the optional shot renderer; no caller-supplied code or URLs."""
import math
from typing import Annotated, Literal
from pydantic import Field, model_validator
from visual_models import Strict, Colour

Text = Annotated[str, Field(min_length=1, max_length=90)]


class ImageRef(Strict):
    asset_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


class Item(Strict):
    label: Text
    detail: str = Field(default='', max_length=100)
    image: ImageRef | None = None


class Heading(Strict):
    title: Text
    subtitle: str = Field(default='', max_length=120)


class Rewrite(Heading):
    kind: Literal['typewriter-rewrite']
    initial: Text
    replacement: Text


class Marker(Heading):
    kind: Literal['marker-title']


class Outline(Heading):
    kind: Literal['outline-title']


class ListReveal(Heading):
    kind: Literal['list-reveal']
    items: list[Item] = Field(min_length=2, max_length=6)


class CardStack(Heading):
    kind: Literal['card-stack']
    items: list[Item] = Field(min_length=2, max_length=4)


class Comparison(Heading):
    kind: Literal['before-after']
    before: ImageRef
    after: ImageRef
    before_label: Text = '调整前'
    after_label: Text = '调整后'


class Datum(Strict):
    label: str = Field(min_length=1, max_length=16)
    value: float = Field(ge=0, le=1e12, allow_inf_nan=False)


class LineChart(Heading):
    kind: Literal['line-chart']
    points: list[Datum] = Field(min_length=2, max_length=8)
    unit: str = Field(default='', max_length=12)
    data_note: str = Field(min_length=1, max_length=1000,
        description='Actual source or explicit simulation declaration; animation does not verify data')


class Split(Heading):
    kind: Literal['split-screen']
    items: list[Item] = Field(min_length=2, max_length=4)


class Counter(Heading):
    kind: Literal['digit-roll']
    value: str = Field(pattern=r'^[-+]?\d[\d,.]{0,11}[%万亿千百倍人次条元秒天年个台件份小时分钟]*$', max_length=24)
    data_note: str = Field(min_length=1, max_length=1000)


Label = Annotated[str, Field(min_length=1, max_length=16)]


class ConceptNetwork(Heading):
    kind: Literal['concept-network']
    center: Label
    nodes: list[Label] = Field(min_length=2, max_length=6)
    direction: Literal['relation', 'inward', 'outward'] = 'relation'


class ConceptMatrix(Heading):
    kind: Literal['concept-matrix']
    label: Label
    rows: int = Field(ge=2, le=5)
    columns: int = Field(ge=2, le=8)
    conclusion: str = Field(min_length=1, max_length=32)
    data_note: str = Field(min_length=1, max_length=1000,
        description='Declare whether repeated icons are schematic or represent measured counts')


class LayeredRings(Heading):
    kind: Literal['layered-rings']
    center: Label
    layers: list[Label] = Field(min_length=1, max_length=3)


class ProcessChain(Heading):
    kind: Literal['process-chain']
    steps: list[Label] = Field(min_length=2, max_length=7)
    step_probability: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    independent_assumption: bool = False
    fail_step: int | None = Field(default=None, ge=1, le=7)
    data_note: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def meaningful_chain(self):
        if self.fail_step is not None and self.fail_step > len(self.steps):
            raise ValueError('Failure step must exist in this chain (one-based index)')
        if self.step_probability is not None:
            if not self.independent_assumption or not self.data_note.strip():
                raise ValueError('Probability product requires an explicit independence assumption and data note')
            if self.fail_step is not None:
                raise ValueError('Use separate shots for an illustrative failure and the probability model')
        elif self.independent_assumption:
            raise ValueError('An independence assumption requires a declared step probability')
        if self.fail_step is not None and not self.data_note.strip():
            raise ValueError('An illustrative failure path needs a data note')
        return self


Shot = Annotated[Rewrite | Marker | Outline | ListReveal | CardStack | Comparison | LineChart | Split | Counter |
                 ConceptNetwork | ConceptMatrix | LayeredRings | ProcessChain,
                 Field(discriminator='kind')]


class ShotRender(Strict):
    request_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    project_revision: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)
    shot: Shot
    width: int = Field(default=1920, ge=320, le=1920)
    height: int = Field(default=1080, ge=320, le=1920)
    fps: Literal[25, 30] = 25
    duration: float = Field(default=5., ge=3., le=12., allow_inf_nan=False)
    background: Colour = '111114'
    foreground: Colour = 'F6F5F2'
    accent: Colour = '6AABFF'
    secondary: Colour = 'F39AB8'
    font_path: str | None = None

    @model_validator(mode='after')
    def coherent(self):
        if self.width % 2 or self.height % 2:
            raise ValueError('Canvas dimensions must be even')
        if not any(abs(self.width / self.height - ratio) < .002 for ratio in (16/9, 9/16, 1)):
            raise ValueError('Use a 16:9, 9:16 or square canvas')
        if isinstance(self.shot, ListReveal) and self.duration < 1.5 + .5 * len(self.shot.items):
            raise ValueError('Give each list item reading time and a final hold')
        if isinstance(self.shot, ProcessChain) and self.duration < 1.5 + .5 * len(self.shot.steps):
            raise ValueError('Give the process steps reading time and a final hold')
        if isinstance(self.shot, LineChart) and any(not math.isfinite(p.value) for p in self.shot.points):
            raise ValueError('Chart data must be finite')
        return self
