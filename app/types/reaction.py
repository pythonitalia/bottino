from typing import TypedDict

THUMBS_UP = "+1"


class ReactionItem(TypedDict):
    type: str
    channel: str
    ts: str


class ReactionEvent(TypedDict):
    type: str
    user: str
    reaction: str
    item_user: str
    event_ts: str
    item: ReactionItem


class ReactionBody(TypedDict):
    token: str
    team_id: str
    api_app_id: str
    event: ReactionEvent
