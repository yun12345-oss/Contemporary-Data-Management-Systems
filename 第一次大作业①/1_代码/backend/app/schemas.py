from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from app.domain.numbers import check_json_numbers


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def bounded_numbers(cls, value):
        check_json_numbers(value)
        return value


class Credentials(StrictModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[\w\-]+$")
    password: str = Field(min_length=8, max_length=128)


class Option(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    label: str = Field(min_length=1, max_length=200)


class RoutingRule(StrictModel):
    condition: dict
    target: str = Field(min_length=1, max_length=64)


class Routing(StrictModel):
    rules: list[RoutingRule] = Field(default_factory=list, max_length=20)
    default_target: str | None = Field(default=None, max_length=64)


class Question(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    type: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=500)
    required: bool = False
    options: list[Option] = Field(default_factory=list, max_length=100)
    validation: dict = Field(default_factory=dict)
    routing: Routing = Field(default_factory=Routing)


class Definition(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    allow_anonymous: bool = False
    allow_repeat: bool = False
    questions: list[Question] = Field(default_factory=list, max_length=100)


class CreateSurvey(StrictModel):
    title: str = Field(default="未命名问卷", min_length=1, max_length=200)


class SaveDraft(StrictModel):
    revision: int = Field(ge=1)
    draft: Definition


class Publish(StrictModel):
    revision: int = Field(ge=1)
    deadline: datetime | None = None

    @field_validator("deadline")
    @classmethod
    def aware(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("截止时间必须包含时区")
        return value


class StatusChange(StrictModel):
    status: Literal["closed"]
    revision: int | None = Field(default=None, ge=1)


class StartAttempt(StrictModel):
    anonymous: bool = False


class AttemptRevision(StrictModel):
    revision: int = Field(ge=1, strict=True)


class SaveAttempt(AttemptRevision):
    answers: dict = Field(max_length=100)
    current_question_id: str | None = Field(default=None, max_length=64)


class Submit(StrictModel):
    token: str = Field(max_length=4096)
    answers: dict = Field(max_length=100)


class QueryWindow(StrictModel):
    version: int | None = None
