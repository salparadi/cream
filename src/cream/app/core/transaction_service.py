import asyncio
import base64
from eth_account._utils.typed_transactions import TypedTransaction
from eth_account._utils.legacy_transactions import Transaction, vrs_from
from eth_account._utils.signing import hash_of_signed_transaction
from eth_account import Account
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from typing import List
import ujson
import websockets
import web3

from .app_state import AppState
from ...config.logger import logger

log = logger(__name__)


class TransactionService:
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.w3 = self.app_state.w3

        self.failed_transactions = self.app_state.failed_transactions
        self.finalized_transactions = self.app_state.finalized_transactions
        self.pending_transactions = self.app_state.pending_transactions

        self.sequencer_uri = self.app_state.chain_info.get("sequencer_uri")
        self.websocket_uri = self.app_state.chain_info.get("websocket_uri")
        self.routers = self.app_state.chain_info.get("routers")

        log.info(
            f"TransactionService initialized with app instance at {id(self.app_state)}"
        )

    def get_int_value(self, value):
        try:
            # Check if the value is already an integer
            return int(value)
        except ValueError:
            # If not, assume it's hex and convert
            return int(value, 16)

    async def watch_transactions(self):

        while True:
            try:
                if self.app_state.chain_name == "arbitrum":
                    await self.watch_arbitrum_sequencer_transactions(self.sequencer_uri)

                elif (
                    self.app_state.chain_name == "base"
                    and self.app_state.node == "node"
                ):
                    await self.watch_node_pending_transactions()

                elif self.app_state.chain_name == "ethereum":
                    if self.app_state.node == "node":
                        await self.watch_node_pending_transactions()
                    elif self.app_state.node == "alchemy":
                        await self.watch_alchemy_pending_transactions()

                elif (
                    self.app_state.chain_name == "optimism"
                    and self.app_state.node == "node"
                ):
                    await self.watch_node_pending_transactions()

                elif self.app_state.chain_name == "polygon":
                    if self.app_state.node == "node":
                        await self.watch_node_pending_transactions()
                    elif self.app_state.node == "alchemy":
                        await self.watch_alchemy_pending_transactions()

            except websockets.ConnectionClosed:
                log.exception(
                    "(watch_pending_transactions) (websockets.ConnectionClosed) reconnecting...)"
                )
                continue
            except asyncio.CancelledError:
                log.info("Pending transaction watcher cancelled, shutting down")
                break
            except Exception as exc:
                log.exception(f"(watch_pending_transactions) (catch-all): {exc}")
                continue

    async def watch_alchemy_pending_transactions(self):
        async for websocket in websockets.client.connect(
            uri=self.websocket_uri, ping_timeout=None, max_queue=None
        ):
            await websocket.send(
                ujson.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_subscribe",
                        "params": [
                            "alchemy_pendingTransactions",
                        ],
                    }
                )
            )
            subscription_id = ujson.loads(await websocket.recv())["result"]
            log.info(f"Subscription Active: Pending Transactions - {subscription_id}")

            while True:
                try:
                    message = ujson.loads(await websocket.recv())

                    pending_transaction = message["params"]["result"]
                    pending_transaction_hash = pending_transaction.get("hash")

                    if pending_transaction_hash not in self.failed_transactions:
                        await self.pending_transactions.put(pending_transaction)

                except websockets.WebSocketException:
                    log.exception(
                        "(watch_pending_transactions) (websockets.WebSocketException)"
                    )
                    break  # escape the loop to reconnect
                except asyncio.TimeoutError:
                    log.exception("(watch_pending_transactions) (asyncio.TimeoutError)")
                    break  # escape the loop to reconnect
                except Exception as exc:
                    log.exception(
                        f"(watch_pending_transactions) (websocket.recv): {exc}"
                    )

                await asyncio.sleep(0.01)

    async def watch_arbitrum_sequencer_transactions(self, sequencer_uri: str):

        def decode_arbitrum_transaction(raw_tx, tx_hash):
            tx_bytes = HexBytes(raw_tx)
            if len(tx_bytes) > 0 and tx_bytes[0] <= 0x7F:
                # We are dealing with a typed transaction.
                tx_type = 2
                tx = TypedTransaction.from_bytes(tx_bytes)
                # tx_hash = tx.hash()
                vrs = tx.vrs()
            else:
                # We are dealing with a legacy transaction.
                tx_type = 0
                tx = Transaction.from_bytes(tx_bytes)
                # tx_hash = hash_of_signed_transaction(tx)
                vrs = vrs_from(tx)

            # extracting sender address
            sender = Account._recover_hash(tx_hash, vrs=vrs)

            # adding sender to result and cleaning
            res = tx.as_dict()
            res["from"] = sender
            res["to"] = res["to"].hex()
            res["data"] = res["data"].hex()
            res["type"] = res.get("type", tx_type)
            res["hash"] = tx_hash

            return res

        async for websocket in websockets.connect(
            uri=sequencer_uri, ping_timeout=None, max_queue=None
        ):
            while True:
                try:
                    sequencer_payload = ujson.loads(await websocket.recv())
                except Exception as e:
                    log.error(f"(watch_arbitrum_transactions) websocket.recv(): {e}")
                    break
                else:
                    try:
                        messages = sequencer_payload["messages"]
                    except KeyError as e:
                        continue
                    else:
                        for message in messages:
                            try:
                                l1_kind = message["message"]["message"]["header"][
                                    "kind"
                                ]
                                sender = message["message"]["message"]["header"][
                                    "sender"
                                ]
                                block_number = message["message"]["message"]["header"][
                                    "blockNumber"
                                ]
                            except Exception as e:
                                log.info(type(e))

                            if l1_kind != 3:
                                continue

                            l2_message = message["message"]["message"]["l2Msg"]
                            raw_tx = HexBytes(base64.b64decode(l2_message))
                            l2_message_type = raw_tx[0]

                            if l2_message_type != 4:
                                continue

                            decoded_tx = None

                            try:
                                tx_bytes = HexBytes(raw_tx[1:])
                                tx_hash = self.w3.keccak(raw_tx[1:]).hex()
                                pending_transaction = decode_arbitrum_transaction(
                                    tx_bytes, tx_hash
                                )
                            except Exception as exc:
                                log.error(exc)
                                continue
                            else:
                                await self.pending_transactions.put(pending_transaction)

                await asyncio.sleep(0.01)  # Yield control back to the event loop

    async def watch_node_pending_transactions(self):
        async for websocket in websockets.client.connect(
            uri=self.websocket_uri, ping_timeout=None, max_queue=None
        ):
            await websocket.send(
                ujson.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_subscribe",
                        "params": [
                            "newPendingTransactions",
                            True,
                        ],
                    }
                )
            )
            subscription_id = ujson.loads(await websocket.recv())["result"]
            log.info(f"Subscription Active: Pending Transactions - {subscription_id}")

            while True:
                try:
                    message = ujson.loads(await websocket.recv())

                    pending_transaction = message["params"]["result"]
                    pending_transaction_hash = pending_transaction.get("hash")

                    if pending_transaction_hash not in self.failed_transactions:
                        await self.pending_transactions.put(pending_transaction)

                except websockets.WebSocketException:
                    log.exception(
                        "(watch_pending_transactions) (websockets.WebSocketException)"
                    )
                    break  # escape the loop to reconnect
                except asyncio.TimeoutError:
                    log.exception("(watch_pending_transactions) (asyncio.TimeoutError)")
                    break  # escape the loop to reconnect
                except Exception as exc:
                    log.exception(
                        f"(watch_pending_transactions) (websocket.recv): {exc}"
                    )

                await asyncio.sleep(0.01)  # Yield control back to the event loop

    async def process_pending_transactions(self):
        redis_client = self.app_state.redis_client

        while True:
            transaction = await self.pending_transactions.get()

            if "gasPrice" in transaction:
                transaction_gas_price = self.get_int_value(transaction["gasPrice"])
            elif "maxFeePerGas" in transaction:
                transaction_gas_price = self.get_int_value(transaction["maxFeePerGas"])
            else:
                print("No gas price information available in the transaction.")
                continue

            if transaction_gas_price < self.app_state.base_fee_next:
                continue

            try:
                result = await redis_client.publish(
                    "cream_pending_transactions", ujson.dumps(transaction)
                )
            except Exception as exc:
                log.error(
                    f"(process_pending_transactions) (redis_client.publish) ({type(exc)}): {exc}"
                )

            await asyncio.sleep(0.01)

    async def process_finalized_transactions(self):
        redis_client = self.app_state.redis_client

        while True:
            transaction = await self.finalized_transactions.get()

            try:
                result = await redis_client.publish(
                    "cream_finalized_transactions", ujson.dumps(transaction)
                )
            except Exception as exc:
                log.error(
                    f"(process_finalized_transactions) (redis_client.publish) ({type(exc)}): {exc}"
                )

            await asyncio.sleep(0.01)
