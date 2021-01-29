import asyncio
import httpx

from mangum import Mangum
from typing import Iterable, cast

from slack_bolt.adapter.starlette.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from starlette.applications import Starlette
from starlette.config import Config
from starlette.requests import Request
from starlette.routing import Route

from app.types.message import Element, SlackMessage
from app.types.reaction import THUMBS_UP, ReactionBody

config = Config(".env")

SLACK_SIGNING_SECRET = config("SLACK_SIGNING_SECRET", cast=str)
SLACK_BOT_TOKEN = config("SLACK_BOT_TOKEN", cast=str)
IFFFT_WEBHOOK = config("IFFFT_WEBHOOK", cast=str)

app = AsyncApp(signing_secret=SLACK_SIGNING_SECRET, token=SLACK_BOT_TOKEN)


async def store_link(link: str, message: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            IFFFT_WEBHOOK, json={"value1": message, "value2": link}
        )
        response.raise_for_status()


def get_links_from_message(message: SlackMessage) -> Iterable[str]:
    blocks = message.get("blocks", None) or []

    for block in blocks:
        for element in block["elements"]:
            elements = cast(list[Element], element.get("elements", []))

            for child_element in elements:
                if child_element["type"] == "link":
                    yield cast(str, child_element["url"])


@app.event("reaction_added")  # type: ignore
async def handle_reaction(body: ReactionBody, client: AsyncWebClient, logger):
    reaction = body["event"]["reaction"]

    if reaction != THUMBS_UP:
        return

    channel = body["event"]["item"]["channel"]
    channel_info = await client.conversations_info(channel=channel)
    name = channel_info["channel"]["name"]

    if name != "newsletter":
        return

    message_ts = body["event"]["item"]["ts"]

    response = await client.conversations_history(
        channel=channel, oldest=message_ts, limit=1, inclusive=True
    )
    message: SlackMessage = response["messages"][0]
    links = list(get_links_from_message(message))

    if not links:
        return

    total_reactions = sum(
        r["count"] for r in message["reactions"] if r["name"] == THUMBS_UP
    )

    if total_reactions >= 2:
        p = [store_link(link=link, message=message["text"]) for link in links]

        await asyncio.gather(*p)


@app.event("app_mention")  # type: ignore
async def handle_app_mentions(body, say, logger):
    logger.info(body)
    await say("What's up?")


app_handler = AsyncSlackRequestHandler(app)


async def endpoint(req: Request):
    return await app_handler.handle(req)


api = Starlette(
    debug=True, routes=[Route("/slack/events", endpoint=endpoint, methods=["POST"])]
)

handler = Mangum(api)
