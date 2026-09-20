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

    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "native": "ETH",
        "alchemy": "https://eth-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://ethereum-rpc.publicnode.com",
        "dex_id": "ethereum",
    },

    "base": {
        "name": "Base",
        "chain_id": 8453,
        "native": "ETH",
        "alchemy": "https://base-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://base-rpc.publicnode.com",
        "dex_id": "base",
    },

    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "native": "ETH",
        "alchemy": "https://arb-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://arbitrum-one-rpc.publicnode.com",
        "dex_id": "arbitrum",
    },

    "optimism": {
        "name": "OP Mainnet",
        "chain_id": 10,
        "native": "ETH",
        "alchemy": "https://opt-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://optimism-rpc.publicnode.com",
        "dex_id": "optimism",
    },

    "polygon": {
        "name": "Polygon",
        "chain_id": 137,
        "native": "POL",
        "alchemy": "https://polygon-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://polygon-bor-rpc.publicnode.com",
        "dex_id": "polygon",
    },

    "bnb": {
        "name": "BNB Smart Chain",
        "chain_id": 56,
        "native": "BNB",
        "alchemy": "https://bnb-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://bsc-rpc.publicnode.com",
        "dex_id": "bsc",
    },

    "avalanche": {
        "name": "Avalanche C-Chain",
        "chain_id": 43114,
        "native": "AVAX",
        "alchemy": "https://avax-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://avalanche-c-chain-rpc.publicnode.com",
        "dex_id": "avalanche",
    },

    "linea": {
        "name": "Linea",
        "chain_id": 59144,
        "native": "ETH",
        "alchemy": "https://linea-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://linea-rpc.publicnode.com",
        "dex_id": "linea",
    },

    "zksync": {
        "name": "zkSync Era",
        "chain_id": 324,
        "native": "ETH",
        "alchemy": "https://zksync-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://mainnet.era.zksync.io",
        "dex_id": "zksync",
    },

    "scroll": {
        "name": "Scroll",
        "chain_id": 534352,
        "native": "ETH",
        "alchemy": "https://scroll-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.scroll.io",
        "dex_id": "scroll",
    },

    "mantle": {
        "name": "Mantle",
        "chain_id": 5000,
        "native": "MNT",
        "alchemy": "https://mantle-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.mantle.xyz",
        "dex_id": "mantle",
    },

    "blast": {
        "name": "Blast",
        "chain_id": 81457,
        "native": "ETH",
        "alchemy": "https://blast-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.blast.io",
        "dex_id": "blast",
    },

    "gnosis": {
        "name": "Gnosis",
        "chain_id": 100,
        "native": "XDAI",
        "alchemy": "https://gnosis-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.gnosischain.com",
        "dex_id": "gnosis",
    },

    "celo": {
        "name": "Celo",
        "chain_id": 42220,
        "native": "CELO",
        "alchemy": "https://celo-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://forno.celo.org",
        "dex_id": "celo",
    },

    "unichain": {
        "name": "Unichain",
        "chain_id": 130,
        "native": "ETH",
        "alchemy": "https://unichain-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://mainnet.unichain.org",
        "dex_id": "unichain",
    },

    "worldchain": {
        "name": "World Chain",
        "chain_id": 480,
        "native": "ETH",
        "alchemy": "https://worldchain-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://worldchain-mainnet.g.alchemy.com/v2/{key}",
        "dex_id": "worldchain",
    },

    "soneium": {
        "name": "Soneium",
        "chain_id": 1868,
        "native": "ETH",
        "alchemy": "https://soneium-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.soneium.org",
        "dex_id": "soneium",
    },

    "shape": {
        "name": "Shape",
        "chain_id": 360,
        "native": "ETH",
        "alchemy": "https://shape-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://mainnet.shape.network",
        "dex_id": "shape",
    },

    "sonic": {
        "name": "Sonic",
        "chain_id": 146,
        "native": "S",
        "alchemy": "https://sonic-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.soniclabs.com",
        "dex_id": "sonic",
    },

    "berachain": {
        "name": "Berachain",
        "chain_id": 80094,
        "native": "BERA",
        "alchemy": "https://berachain-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.berachain.com",
        "dex_id": "berachain",
    },

    "monad": {
        "name": "Monad",
        "chain_id": 143,
        "native": "MON",
        "alchemy": "https://monad-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.monad.xyz",
        "dex_id": "monad",
    },

    # ========================================================
    # REQUESTED CHAINS
    # ========================================================

    "robinhood": {
        "name": "Robinhood Chain",
        "chain_id": 4663,
        "native": "ETH",
        "alchemy": "https://robinhood-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.mainnet.chain.robinhood.com",
        "dex_id": "robinhood",
    },

    "arc": {
        "name": "Arc",
        "chain_id": 5042,
        "native": "USDC",
        "alchemy": "https://arc-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc.arc.network",
        "dex_id": "arc",
    },

    "ink": {
        "name": "Ink",
        "chain_id": 57073,
        "native": "ETH",
        "alchemy": "https://ink-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://rpc-gel.inkonchain.com",
        "dex_id": "ink",
    },

    "abstract": {
        "name": "Abstract",
        "chain_id": 2741,
        "native": "ETH",
        "alchemy": "https://abstract-mainnet.g.alchemy.com/v2/{key}",
        "fallback": "https://api.mainnet.abs.xyz",
        "dex_id": "abstract",
    },
}


# ============================================================
# RPC
# ============================================================

async def rpc_call(
    session: aiohttp.ClientSession,
    chain: Dict[str, Any],
    method: str,
    params: List[Any],
) -> Any:

    urls = []

    if ALCHEMY_API_KEY and chain.get("alchemy"):
        urls.append(
            chain["alchemy"].format(key=ALCHEMY_API_KEY)
        )

    if chain.get("fallback") and chain["fallback"] not in urls:
        urls.append(chain["fallback"])

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    for url in urls:

        try:

            timeout = aiohttp.ClientTimeout(total=15)

            async with session.post(
                url,
                json=payload,
                timeout=timeout,
            ) as response:

                if response.status != 200:
                    continue

                data = await response.json(
                    content_type=None
                )

                if "error" in data:
                    continue

                return data.get("result")

        except Exception as exc:
            logger.debug(
                "RPC error on %s: %s",
                chain["name"],
                exc,
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

    if not code or code in ("0x", "0x0"):
        return None

    return {
        "chain_key": chain_key,
        "chain": chain["name"],
        "chain_id": chain["chain_id"],
        "native": chain["native"],
        "contract": address,
    }


async def discover_chains(
    address: str,
) -> List[Dict[str, Any]]:

    timeout = aiohttp.ClientTimeout(total=20)

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
# TOKEN METADATA
# ============================================================

async def get_token_metadata(
    session: aiohttp.ClientSession,
    chain: Dict[str, Any],
    token_address: str,
) -> Dict[str, Any]:

    # Alchemy Token API method.
    # It works through the same chain-specific Alchemy RPC
    # endpoint when that network supports the method.

    result = await rpc_call(
        session,
        chain,
        "alchemy_getTokenMetadata",
        [token_address],
    )

    if isinstance(result, dict):

        return {
            "name": result.get("name"),
            "symbol": result.get("symbol"),
            "decimals": result.get("decimals"),
            "logo": result.get("logo"),
        }

    # --------------------------------------------------------
    # Fallback: standard ERC-20 calls
    # --------------------------------------------------------

    async def eth_call(
        data: str,
    ) -> Any:

        return await rpc_call(
            session,
            chain,
            "eth_call",
            [
                {
                    "to": token_address,
                    "data": data,
                },
                "latest",
            ],
        )

    # ERC-20 selectors:
    # name()     = 0x06fdde03
    # symbol()   = 0x95d89b41
    # decimals() = 0x313ce567

    async def decode_string(result: Any) -> str | None:

        if not result or result == "0x":
            return None

        try:

            raw = bytes.fromhex(
                result[2:]
            )

            # ABI dynamic string
            if len(raw) >= 64:

                offset = int.from_bytes(
                    raw[0:32],
                    "big",
                )

                if (
                    offset + 32 <= len(raw)
                ):

                    length = int.from_bytes(
                        raw[offset:offset + 32],
                        "big",
                    )

                    start = offset + 32
                    end = start + length

                    if end <= len(raw):

                        return raw[
                            start:end
                        ].decode(
                            "utf-8",
                            errors="ignore",
                        ).strip("\x00")

            # Some older tokens return bytes32
            return raw.rstrip(
                b"\x00"
            ).decode(
                "utf-8",
                errors="ignore",
            ).strip()

        except Exception:
            return None

    name_result = await eth_call(
        "0x06fdde03"
    )

    symbol_result = await eth_call(
        "0x95d89b41"
    )

    decimals_result = await eth_call(
        "0x313ce567"
    )

    name = await decode_string(
        name_result
    )

    symbol = await decode_string(
        symbol_result
    )

    decimals = None

    if decimals_result:

        try:
            decimals = int(
                decimals_result,
                16,
            )

        except Exception:
            decimals = None

    return {
        "name": name,
        "symbol": symbol,
        "decimals": decimals,
        "logo": None,
    }


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

        value = int(
            result,
            16,
        ) / 10**18

        return (
            f"{value:.6f} "
            f"{chain['native']}"
        )

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
        return int(
            result,
            16,
        )

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
        return int(
            result,
            16,
        )

    except Exception:
        return None


# ============================================================
# DEXSCREENER MARKET DATA
# ============================================================

async def get_market_data(
    session: aiohttp.ClientSession,
    token_address: str,
    chain_key: str,
) -> List[Dict[str, Any]]:

    chain = EVM_CHAINS[chain_key]

    dex_chain_id = chain.get(
        "dex_id",
        chain_key,
    )

    # DexScreener's documented token endpoint.
    url = (
        "https://api.dexscreener.com/"
        f"tokens/v1/{dex_chain_id}/{token_address}"
    )

    try:

        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(
                total=15
            ),
        ) as response:

            if response.status != 200:
                return []

            data = await response.json(
                content_type=None
            )

    except Exception as exc:

        logger.debug(
            "DexScreener error: %s",
            exc,
        )

        return []

    if not isinstance(data, list):
        return []

    return data[:5]


# ============================================================
# TOKEN ANALYSIS
# ============================================================

async def analyze_token(
    token_address: str,
) -> Dict[str, Any]:

    token_address = token_address.strip()

    if not ADDRESS_RE.fullmatch(
        token_address
    ):

        return {
            "success": False,
            "error": "Invalid EVM address.",
        }

    found = await discover_chains(
        token_address
    )

    if not found:

        return {
            "success": False,
            "error": (
                "I couldn't find a deployed "
                "contract at that address on "
                "the supported EVM networks."
            ),
        }

    if len(found) > 1:

        return {
            "success": False,
            "multiple_chains": True,
            "matches": found,
        }

    detected = found[0]

    chain_key = detected[
        "chain_key"
    ]

    chain = EVM_CHAINS[
        chain_key
    ]

    timeout = aiohttp.ClientTimeout(
        total=20
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        (
            metadata,
            balance,
            tx_count,
            latest_block,
            markets,
        ) = await asyncio.gather(

            get_token_metadata(
                session,
                chain,
                token_address,
            ),

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

    return {
        "success": True,

        "chain_key": chain_key,
        "chain": detected["chain"],
        "chain_id": detected["chain_id"],
        "native": detected["native"],

        "contract": token_address,

        "name": metadata.get(
            "name"
        ),

        "symbol": metadata.get(
            "symbol"
        ),

        "decimals": metadata.get(
            "decimals"
        ),

        "logo": metadata.get(
            "logo"
        ),

        "native_balance": balance,
        "transaction_count": tx_count,
        "latest_block": latest_block,

        "markets": markets,
    }


# ============================================================
# FORMAT RESPONSE
# ============================================================

def format_analysis(
    result: Dict[str, Any]
) -> str:

    if not result.get("success"):

        if result.get(
            "multiple_chains"
        ):

            matches = result.get(
                "matches",
                []
            )

            lines = [
                "⚠️ This contract exists on "
                "multiple supported EVM networks.",
                "",
                "Detected networks:",
            ]

            for match in matches:

                lines.append(
                    f"• {match['chain']} "
                    f"(Chain ID: "
                    f"{match['chain_id']})"
                )

            lines.extend([
                "",
                "The same EVM address can exist "
                "on multiple chains, so I won't "
                "silently guess the network."
            ])

            return "\n".join(
                lines
            )

        return (
            "❌ Analysis failed.\n\n"
            f"{result.get('error', 'Unknown error.')}"
        )

    name = (
        result.get("name")
        or "Unknown Token"
    )

    symbol = (
        result.get("symbol")
        or "?"
    )

    decimals = result.get(
        "decimals"
    )

    lines = [

        "🤖 Web3 Oasis — Token Analysis",

        "",

        f"🪙 {name} ({symbol})",

        f"⛓️ Chain: "
        f"{result['chain']}",

        f"🆔 Chain ID: "
        f"{result['chain_id']}",

        f"📜 Contract: "
        f"{result['contract']}",

    ]

    if decimals is not None:

        lines.append(
            f"🔢 Decimals: {decimals}"
        )

    lines.extend([

        "",

        f"💰 Native Balance: "
        f"{result['native_balance']}",
    ])

    tx_count = result.get(
        "transaction_count"
    )

    if tx_count is not None:

        lines.append(
            f"🔢 Transaction Count: "
            f"{tx_count}"
        )

    latest_block = result.get(
        "latest_block"
    )

    if latest_block is not None:

        lines.append(
            f"🧱 Latest Block: "
            f"{latest_block}"
        )

    markets = result.get(
        "markets"
    ) or []

    if markets:

        lines.extend([
            "",
            "📊 Market Data",
        ])

        for pair in markets:

            base = (
                pair.get(
                    "baseToken"
                )
                or {}
            )

            quote = (
                pair.get(
                    "quoteToken"
                )
                or {}
            )

            pair_name = (
                f"{base.get('symbol', '?')}/"
                f"{quote.get('symbol', '?')}"
            )

            price = pair.get(
                "priceUsd"
            )

            liquidity = (
                pair.get(
                    "liquidity"
                )
                or {}
            ).get("usd")

            volume = (
                pair.get(
                    "volume"
                )
                or {}
            ).get("h24")

            price_change = (
                pair.get(
                    "priceChange"
                )
                or {}
            ).get("h24")

            market_cap = pair.get(
                "marketCap"
            )

            fdv = pair.get(
                "fdv"
            )

            dex = pair.get(
                "dexId"
            )

            pair_url = pair.get(
                "url"
            )

            lines.append(
                f"• Pair: {pair_name}"
            )

            if dex:
                lines.append(
                    f"  DEX: {dex}"
                )

            if price:
                lines.append(
                    f"  Price: ${price}"
                )

            if price_change is not None:
                lines.append(
                    f"  24h Change: "
                    f"{price_change}%"
                )

            if liquidity is not None:
                lines.append(
                    f"  Liquidity: "
                    f"${liquidity:,.2f}"
                )

            if volume is not None:
                lines.append(
                    f"  24h Volume: "
                    f"${volume:,.2f}"
                )

            if market_cap is not None:
                lines.append(
                    f"  Market Cap: "
                    f"${market_cap:,.2f}"
                )

            if fdv is not None:
                lines.append(
                    f"  FDV: "
                    f"${fdv:,.2f}"
                )

            if pair_url:
                lines.append(
                    f"  🔗 {pair_url}"
                )

    else:

        lines.extend([
            "",
            "📊 Market Data: "
            "No DexScreener pair found."
        ])

    return "\n".join(lines)