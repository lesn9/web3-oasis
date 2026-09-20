import os
import asyncio
import logging
import re
from typing import Any, Dict, List

import aiohttp


logger = logging.getLogger(__name__)

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "").strip()

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


# ============================================================
# SUPPORTED EVM NETWORKS
# ============================================================

EVM_CHAINS: Dict[str, Dict[str, Any]] = {

    # --------------------------------------------------------
    # Ethereum
    # --------------------------------------------------------
    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "native": "ETH",
        "alchemy": "https://eth-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://ethereum-rpc.publicnode.com",
    },

    # --------------------------------------------------------
    # Base
    # --------------------------------------------------------
    "base": {
        "name": "Base",
        "chain_id": 8453,
        "native": "ETH",
        "alchemy": "https://base-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://base-rpc.publicnode.com",
    },

    # --------------------------------------------------------
    # Arbitrum
    # --------------------------------------------------------
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "native": "ETH",
        "alchemy": "https://arb-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://arbitrum-one-rpc.publicnode.com",
    },

    # --------------------------------------------------------
    # Optimism
    # --------------------------------------------------------
    "optimism": {
        "name": "OP Mainnet",
        "chain_id": 10,
        "native": "ETH",
        "alchemy": "https://opt-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://optimism-rpc.publicnode.com",
    },

    # --------------------------------------------------------
    # Polygon
    # --------------------------------------------------------
    "polygon": {
        "name": "Polygon",
        "chain_id": 137,
        "native": "POL",
        "alchemy": "https://polygon-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://polygon-bor-rpc.publicnode.com",
    },

    # --------------------------------------------------------
    # BNB Smart Chain
    # --------------------------------------------------------
    "bnb": {
        "name": "BNB Smart Chain",
        "chain_id": 56,
        "native": "BNB",
        "alchemy": "https://bnb-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://bsc-rpc.publicnode.com",
    },

    # --------------------------------------------------------
    # Avalanche
    # --------------------------------------------------------
    "avalanche": {
        "name": "Avalanche C-Chain",
        "chain_id": 43114,
        "native": "AVAX",
        "alchemy": "https://avax-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://avalanche-c-chain-rpc.publicnode.com",
    },

    # --------------------------------------------------------
    # Linea
    # --------------------------------------------------------
    "linea": {
        "name": "Linea",
        "chain_id": 59144,
        "native": "ETH",
        "alchemy": "https://linea-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://linea-rpc.publicnode.com",
    },

    # --------------------------------------------------------
    # zkSync
    # --------------------------------------------------------
    "zksync": {
        "name": "zkSync Era",
        "chain_id": 324,
        "native": "ETH",
        "alchemy": "https://zksync-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://mainnet.era.zksync.io",
    },

    # --------------------------------------------------------
    # Scroll
    # --------------------------------------------------------
    "scroll": {
        "name": "Scroll",
        "chain_id": 534352,
        "native": "ETH",
        "alchemy": "https://scroll-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.scroll.io",
    },

    # --------------------------------------------------------
    # Mantle
    # --------------------------------------------------------
    "mantle": {
        "name": "Mantle",
        "chain_id": 5000,
        "native": "MNT",
        "alchemy": "https://mantle-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.mantle.xyz",
    },

    # --------------------------------------------------------
    # Blast
    # --------------------------------------------------------
    "blast": {
        "name": "Blast",
        "chain_id": 81457,
        "native": "ETH",
        "alchemy": "https://blast-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.blast.io",
    },

    # --------------------------------------------------------
    # Gnosis
    # --------------------------------------------------------
    "gnosis": {
        "name": "Gnosis",
        "chain_id": 100,
        "native": "XDAI",
        "alchemy": "https://gnosis-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.gnosischain.com",
    },

    # --------------------------------------------------------
    # Celo
    # --------------------------------------------------------
    "celo": {
        "name": "Celo",
        "chain_id": 42220,
        "native": "CELO",
        "alchemy": "https://celo-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://forno.celo.org",
    },

    # --------------------------------------------------------
    # Unichain
    # --------------------------------------------------------
    "unichain": {
        "name": "Unichain",
        "chain_id": 130,
        "native": "ETH",
        "alchemy": "https://unichain-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://mainnet.unichain.org",
    },

    # --------------------------------------------------------
    # World Chain
    # --------------------------------------------------------
    "worldchain": {
        "name": "World Chain",
        "chain_id": 480,
        "native": "ETH",
        "alchemy": "https://worldchain-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://worldchain-mainnet.g.alchemy.com/v2/{key}",
    },

    # --------------------------------------------------------
    # Soneium
    # --------------------------------------------------------
    "soneium": {
        "name": "Soneium",
        "chain_id": 1868,
        "native": "ETH",
        "alchemy": "https://soneium-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.soneium.org",
    },

    # --------------------------------------------------------
    # Shape
    # --------------------------------------------------------
    "shape": {
        "name": "Shape",
        "chain_id": 360,
        "native": "ETH",
        "alchemy": "https://shape-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://mainnet.shape.network",
    },

    # --------------------------------------------------------
    # Sonic
    # --------------------------------------------------------
    "sonic": {
        "name": "Sonic",
        "chain_id": 146,
        "native": "S",
        "alchemy": "https://sonic-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.soniclabs.com",
    },

    # --------------------------------------------------------
    # Berachain
    # --------------------------------------------------------
    "berachain": {
        "name": "Berachain",
        "chain_id": 80094,
        "native": "BERA",
        "alchemy": "https://berachain-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.berachain.com",
    },

    # --------------------------------------------------------
    # Monad
    # --------------------------------------------------------
    "monad": {
        "name": "Monad",
        "chain_id": 143,
        "native": "MON",
        "alchemy": "https://monad-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.monad.xyz",
    },

    # ========================================================
    # THE FOUR CHAINS YOU SPECIFICALLY REQUESTED
    # ========================================================

    # --------------------------------------------------------
    # Robinhood Chain
    # --------------------------------------------------------
    "robinhood": {
        "name": "Robinhood Chain",
        "chain_id": 4663,
        "native": "ETH",
        "alchemy": "https://robinhood-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.mainnet.chain.robinhood.com",
    },

    # --------------------------------------------------------
    # Arc
    # --------------------------------------------------------
    "arc": {
        "name": "Arc",
        "chain_id": 5042,
        "native": "USDC",
        "alchemy": "https://arc-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.arc.network",
    },

    # --------------------------------------------------------
    # Ink
    # --------------------------------------------------------
    "ink": {
        "name": "Ink",
        "chain_id": 57073,
        "native": "ETH",
        "alchemy": "https://ink-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc-gel.inkonchain.com",
    },

    # --------------------------------------------------------
    # Abstract
    # --------------------------------------------------------
    "abstract": {
        "name": "Abstract",
        "chain_id": 2741,
        "native": "ETH",
        "alchemy": "https://abstract-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://api.mainnet.abs.xyz",
    },
}


# ============================================================
# RPC HELPERS
# ============================================================

def build_rpc_url(chain: Dict[str, Any]) -> str:
    """
    Prefer Alchemy when an API key is configured.
    Otherwise use the chain's public fallback RPC.
    """

    if ALCHEMY_API_KEY and chain.get("alchemy"):
        return chain["alchemy"].format(key=ALCHEMY_API_KEY)

    return chain["fallback"]


async def rpc_call(
    session: aiohttp.ClientSession,
    chain: Dict[str, Any],
    method: str,
    params: List[Any],
) -> Any:
    """
    Make a JSON-RPC call.

    If Alchemy is configured and its endpoint fails, automatically
    retry the request against the chain's fallback RPC.
    """

    urls = []

    primary = build_rpc_url(chain)
    fallback = chain.get("fallback")

    if primary:
        urls.append(primary)

    if fallback and fallback not in urls:
        urls.append(fallback)

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    last_error = None

    for url in urls:
        try:
            timeout = aiohttp.ClientTimeout(total=12)

            async with session.post(
                url,
                json=payload,
                timeout=timeout,
            ) as response:

                if response.status != 200:
                    last_error = f"HTTP {response.status}"
                    continue

                data = await response.json(content_type=None)

                if "error" in data:
                    last_error = str(data["error"])
                    continue

                return data.get("result")

        except Exception as exc:
            last_error = str(exc)
            continue

    logger.debug(
        "RPC failed for %s: %s",
        chain.get("name"),
        last_error,
    )

    return None


# ============================================================
# CONTRACT DETECTION
# ============================================================

async def check_contract_on_chain(
    session: aiohttp.ClientSession,
    chain_key: str,
    chain: Dict[str, Any],
    address: str,
) -> Dict[str, Any] | None:

    code = await rpc_call(
        session,
        chain,
        "eth_getCode",
        [address, "latest"],
    )

    if not code:
        return None

    if code in ("0x", "0x0"):
        return None

    return {
        "chain_key": chain_key,
        "chain": chain["name"],
        "chain_id": chain["chain_id"],
        "native": chain["native"],
        "contract": address,
    }


async def discover_chains(address: str) -> List[Dict[str, Any]]:
    """
    Probe every supported network concurrently.

    A contract is considered deployed on a network when
    eth_getCode returns bytecode.
    """

    timeout = aiohttp.ClientTimeout(total=15)

    connector = aiohttp.TCPConnector(
        limit=20,
        ttl_dns_cache=300,
    )

    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
    ) as session:

        tasks = [
            check_contract_on_chain(
                session,
                chain_key,
                chain,
                address,
            )
            for chain_key, chain in EVM_CHAINS.items()
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

    found = []

    for result in results:
        if isinstance(result, dict):
            found.append(result)

    return found


# ============================================================
# BASIC ON-CHAIN DATA
# ============================================================

async def get_native_balance(
    session: aiohttp.ClientSession,
    chain: Dict[str, Any],
    address: str,
) -> str:

    result = await rpc_call(
        session,
        chain,
        "eth_getBalance",
        [address, "latest"],
    )

    if result is None:
        return "Unavailable"

    try:
        value = int(result, 16) / 10**18
        return f"{value:.6f} {chain['native']}"
    except Exception:
        return "Unavailable"


async def get_transaction_count(
    session: aiohttp.ClientSession,
    chain: Dict[str, Any],
    address: str,
) -> int | None:

    result = await rpc_call(
        session,
        chain,
        "eth_getTransactionCount",
        [address, "latest"],
    )

    if result is None:
        return None

    try:
        return int(result, 16)
    except Exception:
        return None


async def get_latest_block(
    session: aiohttp.ClientSession,
    chain: Dict[str, Any],
) -> int | None:

    result = await rpc_call(
        session,
        chain,
        "eth_blockNumber",
        [],
    )

    if result is None:
        return None

    try:
        return int(result, 16)
    except Exception:
        return None


# ============================================================
# DEXSCREENER
# ============================================================

async def get_market_data(
    session: aiohttp.ClientSession,
    token_address: str,
    chain_key: str,
) -> List[Dict[str, Any]]:

    url = (
        "https://api.dexscreener.com/latest/dex/tokens/"
        f"{token_address}"
    )

    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=12),
        ) as response:

            if response.status != 200:
                return []

            data = await response.json()

    except Exception:
        return []

    pairs = data.get("pairs") or []

    # DexScreener uses chain identifiers.
    # Filter when possible, but don't discard everything if the
    # provider uses a naming variation for a supported network.

    matching = [
        pair
        for pair in pairs
        if str(pair.get("chainId", "")).lower()
        == chain_key.lower()
    ]

    return matching[:3] if matching else pairs[:3]


# ============================================================
# TOKEN ANALYSIS
# ============================================================

async def analyze_token(token_address: str) -> Dict[str, Any]:

    token_address = token_address.strip()

    if not ADDRESS_RE.fullmatch(token_address):
        return {
            "success": False,
            "error": "Invalid EVM address.",
        }

    found = await discover_chains(token_address)

    if not found:
        return {
            "success": False,
            "error": (
                "I couldn't find a deployed contract at that "
                "address on the supported EVM networks."
            ),
        }

    # Same address can legitimately exist on multiple EVM chains.
    if len(found) > 1:
        return {
            "success": False,
            "multiple_chains": True,
            "matches": found,
        }

    detected = found[0]

    chain_key = detected["chain_key"]
    chain = EVM_CHAINS[chain_key]

    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        balance, tx_count, latest_block, markets = (
            await asyncio.gather(
                get_native_balance(
                    session,
                    chain,
                    token_address,
                ),
                get_transaction_count(
                    session,
                    chain,
                    token_address,
                ),
                get_latest_block(
                    session,
                    chain,
                ),
                get_market_data(
                    session,
                    token_address,
                    chain_key,
                ),
            )
        )

    return {
        "success": True,
        "chain_key": chain_key,
        "chain": detected["chain"],
        "chain_id": detected["chain_id"],
        "native": detected["native"],
        "contract": token_address,
        "native_balance": balance,
        "transaction_count": tx_count,
        "latest_block": latest_block,
        "markets": markets,
    }


# ============================================================
# RESPONSE FORMATTER
# ============================================================

def format_analysis(result: Dict[str, Any]) -> str:

    if not result.get("success"):

        if result.get("multiple_chains"):
            matches = result.get("matches", [])

            lines = [
                "⚠️ This contract exists on multiple supported EVM networks.",
                "",
                "Detected networks:",
            ]

            for match in matches:
                lines.append(
                    f"• {match['chain']} "
                    f"(Chain ID: {match['chain_id']})"
                )

            lines.extend([
                "",
                "The same EVM address can exist on multiple chains, "
                "so I won't silently guess the network."
            ])

            return "\n".join(lines)

        return (
            "❌ Analysis failed.\n\n"
            f"{result.get('error', 'Unknown error.')}"
        )

    lines = [
        "🤖 Web3 Oasis — Token Analysis",
        "",
        f"⛓️ Chain: {result['chain']}",
        f"🆔 Chain ID: {result['chain_id']}",
        f"📜 Contract: {result['contract']}",
        "",
        f"💰 Native Balance: {result['native_balance']}",
    ]

    tx_count = result.get("transaction_count")

    if tx_count is not None:
        lines.append(
            f"🔢 Transaction Count: {tx_count}"
        )

    latest_block = result.get("latest_block")

    if latest_block is not None:
        lines.append(
            f"🧱 Latest Block: {latest_block}"
        )

    markets = result.get("markets") or []

    if markets:
        lines.extend([
            "",
            "📊 Market Data",
        ])

        for pair in markets:
            base = pair.get("baseToken") or {}
            quote = pair.get("quoteToken") or {}

            pair_name = (
                f"{base.get('symbol', '?')}/"
                f"{quote.get('symbol', '?')}"
            )

            price = pair.get("priceUsd")
            liquidity = (pair.get("liquidity") or {}).get("usd")
            volume = (pair.get("volume") or {}).get("h24")

            lines.append(f"• Pair: {pair_name}")

            if price:
                lines.append(
                    f"  Price: ${price}"
                )

            if liquidity is not None:
                lines.append(
                    f"  Liquidity: ${liquidity:,.2f}"
                )

            if volume is not None:
                lines.append(
                    f"  24h Volume: ${volume:,.2f}"
                )

    else:
        lines.extend([
            "",
            "📊 Market Data: No DexScreener pair found."
        ])

    return "\n".join(lines)