from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    source: "QuestionSource | None" = None


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


class QuestionSource(StrictModel):
    question_id: str = Field(min_length=1, max_length=64)
    question_version_id: str = Field(min_length=1, max_length=64)
    version: int = Field(ge=1)
    survey_id: str = Field(min_length=1, max_length=64)
    instance_id: str = Field(min_length=1, max_length=64)
    imported_by: str = Field(min_length=1, max_length=64)
    imported_at: datetime
    grant_id: str | None = Field(default=None, max_length=64)


Question.model_rebuild()


class QuestionContent(StrictModel):
    type: Literal["single_choice", "multiple_choice", "text", "number"]
    title: str = Field(min_length=1, max_length=500)
    options: list[Option] = Field(default_factory=list, max_length=100)
    validation: dict = Field(default_factory=dict)


class NewQuestion(StrictModel):
    content: QuestionContent
    change_note: str = Field(default="创建题目", max_length=1000)


class NewQuestionVersion(NewQuestion):
    revision: int = Field(ge=1, strict=True)
    parent_version_id: str = Field(min_length=1, max_length=64)


class RestoreQuestion(StrictModel):
    revision: int = Field(ge=1, strict=True)
    parent_version_id: str = Field(min_length=1, max_length=64)
    restored_from_version_id: str = Field(min_length=1, max_length=64)
    change_note: str = Field(default="恢复历史内容", max_length=1000)


class Revision(StrictModel):
    revision: int = Field(ge=1, strict=True)


class ImportQuestion(Revision):
    question_version_id: str = Field(min_length=1, max_length=64)


class InstanceOperation(Revision):
    instance_id: str = Field(min_length=1, max_length=64)


class UpgradeQuestion(InstanceOperation):
    question_version_id: str = Field(min_length=1, max_length=64)


class GrantRequest(StrictModel):
    kind: Literal["use", "aggregate"]
    question_version_id: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=3, max_length=40)
    survey_id: str | None = Field(default=None, max_length=64)


class LibraryRequest(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class EditLibrary(LibraryRequest, Revision):
    pass


class LibraryItemRequest(ImportQuestion):
    position: int = Field(default=0, ge=0, le=100000)


class UpdateLibraryItem(LibraryItemRequest):
    pass
