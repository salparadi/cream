from web3 import Web3

EVENT_SIGNATURES = [
    Web3.keccak(text="Sync(uint112,uint112)").hex(),
    Web3.keccak(text="Mint(address,address,int24,int24,uint128,uint256,uint256)").hex(),
    Web3.keccak(text="Burn(address,int24,int24,uint128,uint256,uint256)").hex(),
    Web3.keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex(),
    Web3.keccak(text="PairCreated(address,address,address,uint256)").hex(),
    Web3.keccak(text="PoolCreated(address,address,uint24,int24,address)").hex(),
]
