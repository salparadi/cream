from aiohttp import ClientSession
import asyncio
from dataclasses import dataclass, field
import redis.asyncio as redis
from typing import Dict, List, Optional, Set
from web3.main import Web3


@dataclass
class AppState:
    average_blocktime: float = 12.0
    base_fee_last: int = 0
    base_fee_next: int = 0
    chain_data: Optional[Dict] = None
    chain_id: Optional[int] = None
    chain_name: Optional[str] = None
    failed_transactions: Set[str] = field(default_factory=set)
    finalized_transactions: asyncio.Queue = asyncio.Queue()
    first_block: int = 0
    first_event: int = 0
    http_session: Optional[ClientSession] = None
    http_uri: Optional[str] = None
    newest_block: int = 0
    newest_block_timestamp: int = 0
    live: bool = False
    node: Optional[str] = None
    pending_transactions: asyncio.Queue = asyncio.Queue()
    redis_client: redis.Redis = field(default=None, init=False)
    watching_blocks: bool = False
    watching_events: bool = False
    websocket_uri: Optional[str] = None
    w3 = Web3


# Create a singleton instance of AppStatus
app_state = AppState()
