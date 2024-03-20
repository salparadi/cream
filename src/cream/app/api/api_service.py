import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import ujson
import uvicorn

from ..core.app_state import AppState
from ...config.logger import logger

log = logger(__name__)

class ApiService:
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.api = FastAPI()
        self.setup_routes()
        self.server = None
        log.info(f"ApiService initialized with app instance at {id(self.app_state)}")
    
    def start_api(self):
        """
        Starts up a FastAPI api server to expose app details to a frontend.
        """
        origins = [
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://localhost",
        ]
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        if not self.server:
            config = uvicorn.Config(app=self.api, host="127.0.0.1", port=8000)
            self.server = uvicorn.Server(config)
        # Note: We don't call asyncio.run here as it's already in a new thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.server.serve())
        loop.close()
    
    def setup_routes(self):
        # Define FastAPI endpoints
        @self.api.get("/")
        async def read_root():
            return {"Hello": "World"}
        
        @self.api.get("/pool-managers/")
        async def get_pool_managers():
            if self.app_state is not None:
                return {"pool_managers": list(self.app_state.pool_managers.keys())}
            return {"error": "App not initialized"}
        
        @self.api.get("/app/")
        async def get_app_state():
            if self.app_state:
                app_state = {
                    #"aggregator_addresses": self.app_state.aggregator_addresses,
                    "average_blocktime": self.app_state.average_blocktime,
                    "base_fee_last": self.app_state.base_fee_last,
                    "base_fee_next": self.app_state.base_fee_next,
                    "chain_id": self.app_state.chain_id,
                    "chain_name": self.app_state.chain_name,
                    "failed_transactions": len(self.app_state.failed_transactions),
                    "finalized_transactions": self.app_state.finalized_transactions.qsize(),
                    "first_block": self.app_state.first_block,
                    "first_event": self.app_state.first_event,
                    "newest_block": self.app_state.newest_block,
                    "newest_block_timestamp": self.app_state.newest_block_timestamp,
                    "live": self.app_state.live,
                    "node": self.app_state.node,
                    "pending_transactions": self.app_state.pending_transactions.qsize(),
                    #"router_addresses": self.app_state.router_addresses,
                    "watching_blocks": self.app_state.watching_blocks,
                    "watching_events": self.app_state.watching_events,
                }
                #print(app_state)
                return app_state
            return {"error": "App not initialized"}
        
        @self.api.on_event("shutdown")
        async def shutdown_event():
            await self.stop_api()
    
    async def stop_api(self):
        """
        Stops the API server.
        """
        if self.server:
            self.server.should_exit = True
