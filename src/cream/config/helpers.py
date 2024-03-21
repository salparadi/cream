import ujson

from .logging import logger

log = logger(__name__)


async def get_redis_value(redis_client, key):
    try:
        result = await redis_client.get(key)
        return ujson.loads(result) if result else None
    except Exception as exc:
        log.error(f"(get_redis_value) ({key}) ({type(exc)}): {exc}")


async def publish_redis_message(redis_client, channel, message):
    try:
        result = await redis_client.publish(channel, ujson.dumps(message))
    except Exception as exc:
        log.error(f"(publish_redis_message) ({channel}) ({type(exc)}): {exc}")


async def set_redis_value(redis_client, key, value):
    try:
        result = await redis_client.set(key, ujson.dumps(value))
    except Exception as exc:
        log.error(f"(set_redis_value) ({key} : {value}) ({type(exc)}): {exc}")


async def update_redis_chain_state(redis_client, app_state):
    relevant_keys = [
        "average_blocktime",
        "base_fee_last",
        "base_fee_next",
        "chain_id",
        "chain_name",
        "first_block",
        "first_event",
        "newest_block",
        "newest_block_timestamp",
        "live",
        "node",
        "watching_blocks",
        "watching_events",
    ]

    # Extract only the relevant parts from the app_state
    blockchain_state = {key: getattr(app_state, key, None) for key in relevant_keys}

    # Serialize and update the Redis store
    serialized_state = ujson.dumps(blockchain_state)
    await redis_client.set("app_state", serialized_state)
