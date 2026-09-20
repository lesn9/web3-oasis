import os
import re
import asyncio
import logging
from typing import Any, Dict, Optional, List


import aiohttp


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")


# ============================================================
# EVM CHAIN REGISTRY
# ============================================================
#
# Web3 Oasis uses standard EVM JSON-RPC.
#
# The important part is that users do NOT need to specify
# the chain when analyzing a contract.
#
# The bot can probe supported EVM networks and determine
# where the contract exists.
#
# ============================================================

EVM_CHAINS = {

    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "rpc": "https://eth-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "base": {
        "name": "Base",
        "chain_id": 8453,
        "rpc": "https://base-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpc": "https://arb-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "optimism": {
        "name": "OP Mainnet",
        "chain_id": 10,
        "rpc": "https://opt-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "polygon": {
        "name": "Polygon",
        "chain_id": 137,
        "rpc": "https://polygon-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "POL",
    },

    "bnb": {
        "name": "BNB Smart Chain",
        "chain_id": 56,
        "rpc": "https://bnb-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "BNB",
    },

    "avalanche": {
        "name": "Avalanche",
        "chain_id": 43114,
        "rpc": "https://avax-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "AVAX",
    },

    "linea": {
        "name": "Linea",
        "chain_id": 59144,
        "rpc": "https://linea-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "zksync": {
        "name": "zkSync Era",
        "chain_id": 324,
        "rpc": "https://zksync-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "scroll": {
        "name": "Scroll",
        "chain_id": 534352,
        "rpc": "https://scroll-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "mantle": {
        "name": "Mantle",
        "chain_id": 5000,
        "rpc": "https://mantle-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "MNT",
    },

    "blast": {
        "name": "Blast",
        "chain_id": 81457,
        "rpc": "https://blast-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "gnosis": {
        "name": "Gnosis",
        "chain_id": 100,
        "rpc": "https://gnosis-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "XDAI",
    },

    "celo": {
        "name": "Celo",
        "chain_id": 42220,
        "rpc": "https://celo-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "CELO",
    },

    "unichain": {
        "name": "Unichain",
        "chain_id": 130,
        "rpc": "https://unichain-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "worldchain": {
        "name": "World Chain",
        "chain_id": 480,
        "rpc": "https://worldchain-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "soneium": {
        "name": "Soneium",
        "chain_id": 1868,
        "rpc": "https://soneium-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "shape": {
        "name": "Shape",
        "chain_id": 360,
        "rpc": "https://shape-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "sonic": {
        "name": "Sonic",
        "chain_id": 146,
        "rpc": "https://sonic-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "S",
    },

    "berachain": {
        "name": "Berachain",
        "chain_id": 80094,
        "rpc": "https://berachain-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "BERA",
    },

    "monad": {
        "name": "Monad",
        "chain_id": 143,
        "rpc": "https://monad-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "MON",
    },

    # ========================================================
    # REQUIRED NETWORKS
    # ========================================================

    "robinhood": {
        "name": "Robinhood Chain",
        "chain_id": 4663,
        "rpc": "https://robinhood-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "arc": {
        "name": "Arc",
        "chain_id": 5042,
        "rpc": "https://arc-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "USDC",
    },

    "ink": {
        "name": "Ink",
        "chain_id": 57073,
        "rpc": "https://ink-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },

    "abstract": {
        "name": "Abstract",
        "chain_id": 2741,
        "rpc": "https://abstract-mainnet.g.alchemy.com/v2/{api_key}",
        "native_symbol": "ETH",
    },
}


# ============================================================
# ADDRESS VALIDATION
# ============================================================

ADDRESS_PATTERN = re.compile(
    r"^0x[a-fA-F0-9]{40}$"
)


def is_valid_address(address: str) -> bool:
    return bool(
        ADDRESS_PATTERN.match(address)
    )


# ============================================================
# RPC REQUEST
# ============================================================

async def rpc_call(
    session: aiohttp.ClientSession,
    chain: str,
    method: str,
    params: list,
) -> Optional[Any]:

    if not ALCHEMY_API_KEY:
        return None

    config = EVM_CHAINS.get(chain)

    if not config:
        return None

    rpc_url = config["rpc"].format(
        api_key=ALCHEMY_API_KEY
    )

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    try:

        async with session.post(
            rpc_url,
            json=payload,
        ) as response:

            if response.status != 200:
                return None

            data = await response.json()

            if "error" in data:
                return None

            return data.get("result")

    except Exception as exc:

        logger.debug(
            "RPC error on %s: %s",
            chain,
            exc,
        )

        return None


# ============================================================
# CONTRACT DETECTION
# ============================================================

async def check_contract_on_chain(
    session: aiohttp.ClientSession,
    chain: str,
    address: str,
) -> Optional[Dict[str, Any]]:

    result = await rpc_call(
        session,
        chain,
        "eth_getCode",
        [
            address,
            "latest",
        ],
    )

    if result is None:
        return None

    # An EVM address with no deployed contract returns 0x.
    if result == "0x":
        return None

    config = EVM_CHAINS[chain]

    return {
        "key": chain,
        "name": config["name"],
        "chain_id": config["chain_id"],
        "native_symbol": config["native_symbol"],
    }


async def discover_chains(
    address: str,
) -> List[Dict[str, Any]]:

    if not ALCHEMY_API_KEY:
        raise RuntimeError(
            "ALCHEMY_API_KEY is not configured."
        )

    timeout = aiohttp.ClientTimeout(
        total=30
    )

    connector = aiohttp.TCPConnector(
        limit=20
    )

    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
    ) as session:

        tasks = [
            check_contract_on_chain(
                session,
                chain,
                address,
            )
            for chain in EVM_CHAINS
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

    found = []

    for result in results:

        if isinstance(
            result,
            dict,
        ):
            found.append(result)

    return found


# ============================================================
# NATIVE BALANCE
# ============================================================

async def get_native_balance(
    session: aiohttp.ClientSession,
    chain: str,
    address: str,
) -> Optional[float]:

    result = await rpc_call(
        session,
        chain,
        "eth_getBalance",
        [
            address,
            "latest",
        ],
    )

    if result is None:
        return None

    try:

        return int(
            result,
            16,
        ) / 10**18

    except (
        ValueError,
        TypeError,
    ):
        return None


# ============================================================
# TRANSACTION COUNT
# ============================================================

async def get_transaction_count(
    session: aiohttp.ClientSession,
    chain: str,
    address: str,
) -> Optional[int]:

    result = await rpc_call(
        session,
        chain,
        "eth_getTransactionCount",
        [
            address,
            "latest",
        ],
    )

    if result is None:
        return None

    try:

        return int(
            result,
            16,
        )

    except (
        ValueError,
        TypeError,
    ):
        return None


# ============================================================
# LATEST BLOCK
# ============================================================

async def get_latest_block(
    session: aiohttp.ClientSession,
    chain: str,
) -> Optional[int]:

    result = await rpc_call(
        session,
        chain,
        "eth_blockNumber",
        [],
    )

    if result is None:
        return None

    try:

        return int(
            result,
            16,
        )

    except (
        ValueError,
        TypeError,
    ):
        return None


# ============================================================
# DEXSCREENER
# ============================================================

DEXSCREENER_TOKEN_URL = (
    "https://api.dexscreener.com/latest/dex/tokens/"
)


async def get_market_data(
    session: aiohttp.ClientSession,
    address: str,
    chain: Optional[str] = None,
) -> Dict[str, Any]:

    url = (
        f"{DEXSCREENER_TOKEN_URL}"
        f"{address}"
    )

    try:

        async with session.get(
            url
        ) as response:

            if response.status != 200:

                return {
                    "success": False,
                    "error": (
                        f"DexScreener HTTP "
                        f"{response.status}"
                    ),
                }

            data = await response.json()

            pairs = (
                data.get("pairs")
                or []
            )

            if chain:

                # DexScreener uses its own chain IDs.
                # Most common EVM identifiers match our
                # registry names.

                pairs = [
                    pair
                    for pair in pairs
                    if pair.get(
                        "chainId"
                    ) == chain
                ]

            formatted = []

            for pair in pairs:

                liquidity = (
                    pair.get(
                        "liquidity"
                    )
                    or {}
                )

                formatted.append(
                    {
                        "chain": pair.get(
                            "chainId"
                        ),
                        "dex": pair.get(
                            "dexId"
                        ),
                        "pair": pair.get(
                            "pairAddress"
                        ),
                        "url": pair.get(
                            "url"
                        ),
                        "price_usd": pair.get(
                            "priceUsd"
                        ),
                        "market_cap": pair.get(
                            "marketCap"
                        ),
                        "fdv": pair.get(
                            "fdv"
                        ),
                        "liquidity_usd": (
                            liquidity.get(
                                "usd"
                            )
                        ),
                        "volume_24h": (
                            pair.get(
                                "volume"
                            )
                            or {}
                        ).get(
                            "h24"
                        ),
                        "price_change_24h": (
                            pair.get(
                                "priceChange"
                            )
                            or {}
                        ).get(
                            "h24"
                        ),
                        "base_token": (
                            pair.get(
                                "baseToken"
                            )
                            or {}
                        ).get(
                            "symbol"
                        ),
                        "quote_token": (
                            pair.get(
                                "quoteToken"
                            )
                            or {}
                        ).get(
                            "symbol"
                        ),
                    }
                )

            return {
                "success": True,
                "found": bool(formatted),
                "pairs": formatted,
            }

    except Exception as exc:

        logger.exception(
            "DexScreener request failed: %s",
            exc,
        )

        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# TOKEN ANALYSIS
# ============================================================

async def analyze_token(
    token_address: str,
) -> Dict[str, Any]:

    token_address = (
        token_address.strip()
    )

    if not is_valid_address(
        token_address
    ):

        return {
            "success": False,
            "error": (
                "That doesn't look like "
                "a valid EVM address."
            ),
        }

    # --------------------------------------------------------
    # STEP 1 — FIND THE CONTRACT
    # --------------------------------------------------------

    chains = await discover_chains(
        token_address
    )

    if not chains:

        return {
            "success": False,
            "error": (
                "I couldn't find a deployed contract "
                "at that address on the supported EVM "
                "networks."
            ),
        }

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # If a contract exists on multiple networks, don't
    # silently choose one.
    # --------------------------------------------------------

    if len(chains) > 1:

        return {
            "success": False,
            "multiple_chains": True,
            "address": token_address,
            "chains": chains,
            "error": (
                "This contract address exists on "
                "multiple supported EVM chains."
            ),
        }

    # --------------------------------------------------------
    # STEP 2 — ANALYZE THE DISCOVERED CHAIN
    # --------------------------------------------------------

    detected = chains[0]

    chain = detected["key"]

    timeout = aiohttp.ClientTimeout(
        total=30
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        balance = await get_native_balance(
            session,
            chain,
            token_address,
        )

        tx_count = await get_transaction_count(
            session,
            chain,
            token_address,
        )

        latest_block = await get_latest_block(
            session,
            chain,
        )

        market = await get_market_data(
            session,
            token_address,
            chain,
        )

    return {

        "success": True,

        "address": token_address,

        "chain": detected,

        "native_balance": balance,

        "transaction_count": tx_count,

        "latest_block": latest_block,

        "market": market,
    }


# ============================================================
# FORMAT ANALYSIS
# ============================================================

def format_analysis(
    data: Dict[str, Any],
) -> str:

    if data.get(
        "multiple_chains"
    ):

        lines = [
            "⚠️ MULTIPLE CHAIN DEPLOYMENTS",
            "",
            "This contract address exists on "
            "more than one supported EVM network.",
            "",
            "📍 Contract:",
            f"`{data.get('address')}`",
            "",
            "⛓️ Found on:",
        ]

        for chain in data.get(
            "chains",
            [],
        ):

            lines.append(
                f"• {chain['name']} "
                f"(Chain ID {chain['chain_id']})"
            )

        lines.extend(
            [
                "",
                "Please specify the chain if you "
                "want a specific deployment analyzed."
            ]
        )

        return "\n".join(
            lines
        )

    if not data.get(
        "success"
    ):

        return (
            "❌ Analysis failed.\n\n"
            f"{data.get('error', 'Unknown error')}"
        )

    address = data.get(
        "address"
    )

    chain = data.get(
        "chain",
        {},
    )

    chain_name = chain.get(
        "name",
        "Unknown",
    )

    chain_id = chain.get(
        "chain_id",
        "Unknown",
    )

    native_symbol = chain.get(
        "native_symbol",
        "ETH",
    )

    balance = data.get(
        "native_balance"
    )

    tx_count = data.get(
        "transaction_count"
    )

    latest_block = data.get(
        "latest_block"
    )

    market = data.get(
        "market",
        {},
    )

    lines = [

        "🔎 TOKEN INTELLIGENCE",

        "",

        f"⛓️ Chain: {chain_name}",

        f"🆔 Chain ID: {chain_id}",

        "",

        "📍 Contract:",

        f"`{address}`",

        "",
    ]

    if balance is not None:

        lines.append(
            f"💰 Contract balance: "
            f"{balance:.6f} {native_symbol}"
        )

    else:

        lines.append(
            "💰 Contract balance: unavailable"
        )

    if tx_count is not None:

        lines.append(
            f"🧾 Transaction count: {tx_count}"
        )

    else:

        lines.append(
            "🧾 Transaction count: unavailable"
        )

    if latest_block is not None:

        lines.append(
            f"🧱 Latest block: {latest_block}"
        )

    lines.append("")

    if market.get(
        "success"
    ):

        if market.get(
            "found"
        ):

            pairs = market.get(
                "pairs",
                [],
            )

            lines.append(
                f"📊 Market pairs: {len(pairs)}"
            )

            for pair in pairs[:3]:

                symbol = (
                    pair.get(
                        "base_token"
                    )
                    or "Unknown"
                )

                dex = (
                    pair.get(
                        "dex"
                    )
                    or "Unknown"
                )

                price = pair.get(
                    "price_usd"
                )

                liquidity = pair.get(
                    "liquidity_usd"
                )

                volume = pair.get(
                    "volume_24h"
                )

                lines.extend(
                    [
                        "",
                        f"🔹 {symbol} / {dex}",
                        (
                            f"Price: "
                            f"${price or 'N/A'}"
                        ),
                        (
                            "Liquidity: $"
                            f"{liquidity or 'N/A'}"
                        ),
                        (
                            "24h Volume: $"
                            f"{volume or 'N/A'}"
                        ),
                    ]
                )

        else:

            lines.append(
                "📊 Market data: "
                "No matching market pairs found."
            )

    else:

        lines.append(
            "📊 Market data unavailable."
        )

    lines.extend(
        [
            "",
            "⚠️ Intelligence data only — "
            "not financial advice.",
        ]
    )

    return "\n".join(
        lines
    )