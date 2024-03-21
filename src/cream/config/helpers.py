import asyncio
import ujson

from .logging import logger

log = logger(__name__)


async def publish_redis_message(redis_client, channel, message):
    try:
        result = await redis_client.publish(channel, ujson.dumps(message))
    except Exception as exc:
        log.error(f"(publish_redis_message) ({channel}) ({type(exc)}): {exc}")
    finally:
        await asyncio.sleep(0)
