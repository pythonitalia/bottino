from typing import Any, Literal, Optional, TypedDict


class Element(TypedDict):
    type: Literal["text", "link"]
    url: Optional[str]
    elements: Optional[list[Any]]


class Block(TypedDict):
    type: str
    elements: list[Element]


class Reaction(TypedDict):
    name: str
    count: int


class SlackMessage(TypedDict):
    text: str
    blocks: Optional[list[Block]]
    reactions: list[Reaction]
