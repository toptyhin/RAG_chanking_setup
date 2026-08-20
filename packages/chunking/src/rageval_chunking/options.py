"""Discriminated chunker options."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter, model_validator


class SemchunkOptions(BaseModel):
    provider: Literal["semchunk"] = "semchunk"
    chunk_size: int = Field(default=512, gt=0)
    overlap: float | int | None = None
    token_counter: str = Field(
        default="words",
        description="words | chars | tiktoken:<encoding>",
    )


class ChunkletOptions(BaseModel):
    provider: Literal["chunklet"] = "chunklet"
    mode: Literal["document", "code"] = "document"
    lang: str = "auto"
    max_tokens: int | None = Field(default=None, ge=12)
    max_sentences: int | None = Field(default=None, ge=1)
    max_section_breaks: int | None = Field(default=None, ge=1)
    max_lines: int | None = Field(default=None, ge=5)
    max_functions: int | None = Field(default=None, ge=1)
    overlap_percent: int = Field(default=20, ge=0, le=75)
    offset: int = Field(default=0, ge=0)
    include_comments: bool = True
    docstring_mode: Literal["summary", "all", "excluded"] = "all"
    strict: bool = True
    token_counter: str = Field(default="words")

    @model_validator(mode="after")
    def _at_least_one_constraint(self) -> ChunkletOptions:
        if self.mode == "document":
            if (
                self.max_tokens is None
                and self.max_sentences is None
                and self.max_section_breaks is None
            ):
                raise ValueError(
                    "chunklet document mode requires at least one of "
                    "max_tokens, max_sentences, max_section_breaks"
                )
        elif (
            self.max_tokens is None
            and self.max_lines is None
            and self.max_functions is None
        ):
            raise ValueError(
                "chunklet code mode requires at least one of "
                "max_tokens, max_lines, max_functions"
            )
        return self


class ReferenceOptions(BaseModel):
    provider: Literal["reference_fixed"] = "reference_fixed"
    size: int = Field(default=512, gt=0)
    overlap: int = Field(default=64, ge=0)

    @model_validator(mode="after")
    def _overlap_lt_size(self) -> ReferenceOptions:
        if self.overlap >= self.size:
            raise ValueError("overlap must be >= 0 and < size")
        return self


ChunkerOptions = Annotated[
    SemchunkOptions | ChunkletOptions | ReferenceOptions,
    Field(discriminator="provider"),
]

_chunker_options_adapter: TypeAdapter[
    SemchunkOptions | ChunkletOptions | ReferenceOptions
] = TypeAdapter(ChunkerOptions)


def parse_chunker_options(
    data: dict[str, Any],
) -> SemchunkOptions | ChunkletOptions | ReferenceOptions:
    """Parse a raw dict into the correct options model."""
    return _chunker_options_adapter.validate_python(data)


PROVIDER_ORDER: tuple[str, ...] = (
    "semchunk",
    "chunklet",
    "reference_fixed",
)

PROVIDER_LABELS: dict[str, str] = {
    "semchunk": "Semchunk",
    "chunklet": "Chunklet",
    "reference_fixed": "Reference (fixed size)",
}

PROVIDER_MODES: dict[str, list[str]] = {
    "semchunk": [],
    "chunklet": ["document", "code"],
    "reference_fixed": [],
}

PROVIDER_OPTION_MODELS: dict[
    str, type[SemchunkOptions | ChunkletOptions | ReferenceOptions]
] = {
    "semchunk": SemchunkOptions,
    "chunklet": ChunkletOptions,
    "reference_fixed": ReferenceOptions,
}
