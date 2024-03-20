import asyncio
from collections import deque
import sys
import ujson
import websockets

from .app_state import AppState
from ...config.logger import logger

log = logger(__name__)

class EventService:
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        log.info(f"EventService initialized with app instance at {id(self.app_state)}")
    
    async def watch_events(self):
        """
        Watches the websocket for new events, parses the events and updates pool liquidity
        information as needed
        """
        redis_client = self.app_state.redis_client
                
        self.event_queue: deque = deque()
        
        websocket_uri = self.app_state.chain_info['websocket_uri']
        
        while True:
            try:
                async for websocket in websockets.client.connect(
                    uri=websocket_uri,
                    ping_timeout=None,
                    max_queue=None,
                ):
                    # reset the status and first block every time we start a new websocket connection
                    self.app_state.watching_events = False
                    self.app_state.first_event = 0
                    
                    await websocket.send(
                        ujson.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "eth_subscribe",
                                "params": ["logs", {}],
                            }
                        )
                    )
                    subscription_id = ujson.loads(await websocket.recv())["result"]
                    log.info(f"Subscription Active: Events - {subscription_id}")
                    self.app_state.watching_events = True
                    
                    while True:
                        # process the queue completely before retrieving any more events if bot is "live"
                        # does not yield to the event loop, so coroutines will remain suspended until the queue is empty
                        if self.app_state.live and self.event_queue:
                            event = self.event_queue.popleft()
                            
                            # Add the event to redis
                            try: 
                                result = await redis_client.publish('cream_events', ujson.dumps(event))
                            except Exception as exc:
                                log.error(f"(watch_events) (redis_client.publish) ({type(exc)}): {exc}")
                            finally:
                                await asyncio.sleep(0)
                                	
                        try:
                            message: dict = ujson.loads(await websocket.recv())
                        except asyncio.exceptions.CancelledError:
                            return
                        except websockets.exceptions.WebSocketException as exc:
                            log.exception(f"(watch_events) (WebSocketException)...\nLatency: {websocket.latency}")
                            log.info("watch_events reconnecting...")
                            break
                        except:
                            log.exception("(watch_events) (catch-all)")
                            sys.exit()
                            
                        if not self.app_state.first_event:
                            self.app_state.first_event = int(
                                message["params"]["result"]["blockNumber"],
                                16,
                            )
                            log.info(f"First event block: {self.app_state.first_event}")
                            
                        try:
                            message["params"]["result"]["topics"][0]
                        except IndexError:
                            # ignore anonymous events (no topic0)
                            continue
                        except:
                            log.exception(f"(event_watcher)\n{message=}")
                            continue
                        else:
                            self.event_queue.append(message)
                        
                        await asyncio.sleep(0.1)
            
            except websockets.ConnectionClosed:
                log.exception("(watch_events) (websockets.ConnectionClosed) reconnecting...)")
                continue
            except asyncio.CancelledError:
                log.info("Event watcher cancelled, shutting down")
                break
            except Exception as exc:
                log.exception(f"(watch_events) (catch-all): {exc}")
                continue