import os
import asyncio
import logging
import re
from typing import Optional, Dict, Any, List

import aiohttp


# ============================================================
# CONFIG
# ============================================================

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "").strip()

# Optional.
# The bot works without this.
# If you later add BLOCKSCOUT_API_KEY, the unified Blockscout
# Pro API can be used for higher-throughput access.
BLOCKSCOUT_API_KEY = os.getenv("BLOCKSCOUT_API_KEY", "").strip()

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web3-oasis")


# ============================================================
# SUPPORTED EVM CHAINS
# ============================================================

EVM_CHAINS = {

    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "native": "ETH",
        "alchemy": "eth-mainnet",
        "rpc": "https://ethereum-rpc.publicnode.com",
        "dex_id": "ethereum",
        "blockscout": "https://eth.blockscout.com/api",
    },

    "base": {
        "name": "Base",
        "chain_id": 8453,
        "native": "ETH",
        "alchemy": "base-mainnet",
        "rpc": "https://base-rpc.publicnode.com",
        "dex_id": "base",
        "blockscout": "https://base.blockscout.com/api",
    },

    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "native": "ETH",
        "alchemy": "arb-mainnet",
        "rpc": "https://arbitrum-one-rpc.publicnode.com",
        "dex_id": "arbitrum",
        "blockscout": "https://arbitrum.blockscout.com/api",
    },

    "optimism": {
        "name": "Optimism",
        "chain_id": 10,
        "native": "ETH",
        "alchemy": "opt-mainnet",
        "rpc": "https://optimism-rpc.publicnode.com",
        "dex_id": "optimism",
        "blockscout": "https://optimism.blockscout.com/api",
    },

    "polygon": {
        "name": "Polygon",
        "chain_id": 137,
        "native": "POL",
        "alchemy": "polygon-mainnet",
        "rpc": "https://polygon-bor-rpc.publicnode.com",
        "dex_id": "polygon",
        "blockscout": "https://polygon.blockscout.com/api",
    },

    "bnb": {
        "name": "BNB Smart Chain",
        "chain_id": 56,
        "native": "BNB",
        "alchemy": "bnb-mainnet",
        "rpc": "https://bsc-rpc.publicnode.com",
        "dex_id": "bsc",
        "blockscout": None,
    },

    "avalanche": {
        "name": "Avalanche",
        "chain_id": 43114,
        "native": "AVAX",
        "alchemy": "avax-mainnet",
        "rpc": "https://avalanche-c-chain-rpc.publicnode.com",
        "dex_id": "avalanche",
        "blockscout": None,
    },

    "linea": {
        "name": "Linea",
        "chain_id": 59144,
        "native": "ETH",
        "alchemy": "linea-mainnet",
        "rpc": "https://linea-rpc.publicnode.com",
        "dex_id": "linea",
        "blockscout": None,
    },

    "zksync": {
        "name": "zkSync Era",
        "chain_id": 324,
        "native": "ETH",
        "alchemy": "zksync-mainnet",
        "rpc": "https://mainnet.era.zksync.io",
        "dex_id": "zksync",
        "blockscout": "https://zksync.blockscout.com/api",
    },

    "scroll": {
        "name": "Scroll",
        "chain_id": 534352,
        "native": "ETH",
        "alchemy": "scroll-mainnet",
        "rpc": "https://rpc.scroll.io",
        "dex_id": "scroll",
        "blockscout": "https://scroll.blockscout.com/api",
    },

    "mantle": {
        "name": "Mantle",
        "chain_id": 5000,
        "native": "MNT",
        "alchemy": "mantle-mainnet",
        "rpc": "https://rpc.mantle.xyz",
        "dex_id": "mantle",
        "blockscout": None,
    },

    "blast": {
        "name": "Blast",
        "chain_id": 81457,
        "native": "ETH",
        "alchemy": "blast-mainnet",
        "rpc": "https://rpc.blast.io",
        "dex_id": "blast",
        "blockscout": None,
    },

    "gnosis": {
        "name": "Gnosis",
        "chain_id": 100,
        "native": "XDAI",
        "alchemy": "gnosis-mainnet",
        "rpc": "https://rpc.gnosischain.com",
        "dex_id": "gnosis",
        "blockscout": "https://gnosis.blockscout.com/api",
    },

    "celo": {
        "name": "Celo",
        "chain_id": 42220,
        "native": "CELO",
        "alchemy": "celo-mainnet",
        "rpc": "https://forno.celo.org",
        "dex_id": "celo",
        "blockscout": "https://explorer.celo.org/mainnet/api",
    },

    "unichain": {
        "name": "Unichain",
        "chain_id": 130,
        "native": "ETH",
        "alchemy": "unichain-mainnet",
        "rpc": "https://mainnet.unichain.org",
        "dex_id": "unichain",
        "blockscout": "https://unichain.blockscout.com/api",
    },

    "worldchain": {
        "name": "World Chain",
        "chain_id": 480,
        "native": "ETH",
        "alchemy": "worldchain-mainnet",
        "rpc": None,
        "dex_id": "worldchain",
        "blockscout": "https://worldchain-mainnet.explorer.alchemy.com/api",
    },

    "soneium": {
        "name": "Soneium",
        "chain_id": 1868,
        "native": "ETH",
        "alchemy": "soneium-mainnet",
        "rpc": "https://rpc.soneium.org",
        "dex_id": "soneium",
        "blockscout": "https://soneium.blockscout.com/api",
    },

    "shape": {
        "name": "Shape",
        "chain_id": 360,
        "native": "ETH",
        "alchemy": "shape-mainnet",
        "rpc": "https://mainnet.shape.network",
        "dex_id": "shape",
        "blockscout": "https://shape.blockscout.com/api",
    },

    "sonic": {
        "name": "Sonic",
        "chain_id": 146,
        "native": "S",
        "alchemy": "sonic-mainnet",
        "rpc": "https://rpc.soniclabs.com",
        "dex_id": "sonic",
        "blockscout": None,
    },

    "berachain": {
        "name": "Berachain",
        "chain_id": 80094,
        "native": "BERA",
        "alchemy": "berachain-mainnet",
        "rpc": "https://rpc.berachain.com",
        "dex_id": "berachain",
        "blockscout": None,
    },

    "monad": {
        "name": "Monad",
        "chain_id": 143,
        "native": "MON",
        "alchemy": "monad-mainnet",
        "rpc": "https://rpc.monad.xyz",
        "dex_id": "monad",
        "blockscout": None,
    },

    # ========================================================
    # REQUIRED NEW CHAINS
    # ========================================================

    "robinhood": {
        "name": "Robinhood Chain",
        "chain_id": 4663,
        "native": "ETH",
        "alchemy": "robinhood-mainnet",
        "rpc": "https://rpc.mainnet.chain.robinhood.com",
        "dex_id": "robinhood",
        "blockscout": "https://robinhoodchain.blockscout.com/api",
    },

    "arc": {
        "name": "Arc",
        "chain_id": 5042,
        "native": "USDC",
        "alchemy": "arc-mainnet",
        "rpc": "https://rpc.arc.network",
        "dex_id": "arc",
        "blockscout": "https://explorer.arc.io/api",
    },

    "ink": {
        "name": "Ink",
        "chain_id": 57073,
        "native": "ETH",
        "alchemy": "ink-mainnet",
        "rpc": "https://rpc-gel.inkonchain.com",
        "dex_id": "ink",
        "blockscout": "https://explorer.inkonchain.com/api",
    },

    "abstract": {
        "name": "Abstract",
        "chain_id": 2741,
        "native": "ETH",
        "alchemy": "abstract-mainnet",
        "rpc": "https://api.mainnet.abs.xyz",
        "dex_id": "abstract",
        "blockscout": None,
    },
}


# ============================================================
# HTTP HELPERS
# ============================================================

async def http_get(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 15,
) -> Optional[Any]:

    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(
                url,
                params=params,
                headers=headers,
            ) as response:

                if response.status != 200:
                    logger.warning(
                        "GET failed %s -> HTTP %s",
                        url,
                        response.status,
                    )
                    return None

                return await response.json(content_type=None)

    except Exception as exc:
        logger.warning("GET error %s: %s", url, exc)
        return None


async def rpc_call(
    chain: Dict[str, Any],
    method: str,
    params: list,
) -> Optional[Any]:

    urls = []

    if ALCHEMY_API_KEY and chain.get("alchemy"):
        urls.append(
            f"https://{chain['alchemy']}.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        )

    if chain.get("rpc"):
        urls.append(chain["rpc"])

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    timeout_obj = aiohttp.ClientTimeout(total=15)

    for url in urls:

        try:

            async with aiohttp.ClientSession(
                timeout=timeout_obj
            ) as session:

                async with session.post(
                    url,
                    json=payload,
                ) as response:

                    if response.status != 200:
                        continue

                    data = await response.json()

                    if "error" in data:
                        continue

                    return data.get("result")

        except Exception:
            continue

    return None


# ============================================================
# CONTRACT DETECTION
# ============================================================

async def check_contract_on_chain(
    chain_key: str,
    chain: Dict[str, Any],
    address: str,
) -> bool:

    code = await rpc_call(
        chain,
        "eth_getCode",
        [address, "latest"],
    )

    return bool(code and code != "0x")


async def discover_chains(address: str) -> List[str]:

    tasks = [
        check_contract_on_chain(
            key,
            chain,
            address,
        )
        for key, chain in EVM_CHAINS.items()
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    matches = []

    for (key, _), result in zip(
        EVM_CHAINS.items(),
        results,
    ):

        if result is True:
            matches.append(key)

    return matches


# ============================================================
# ERC-20 ABI HELPERS
# ============================================================

def encode_address(address: str) -> str:
    return address.lower().replace("0x", "").rjust(64, "0")


def decode_string(result: Optional[str]) -> Optional[str]:

    if not result or result == "0x":
        return None

    try:

        raw = bytes.fromhex(result[2:])

        # ABI dynamic string
        if len(raw) >= 64:

            offset = int.from_bytes(
                raw[0:32],
                "big",
            )

            if offset + 32 <= len(raw):

                length = int.from_bytes(
                    raw[offset:offset + 32],
                    "big",
                )

                start = offset + 32
                end = start + length

                value = raw[start:end].decode(
                    "utf-8",
                    errors="ignore",
                )

                if value:
                    return value.strip()

        # bytes32 fallback
        value = raw.rstrip(b"\x00").decode(
            "utf-8",
            errors="ignore",
        )

        return value.strip() or None

    except Exception:
        return None


async def erc20_call(
    chain: Dict[str, Any],
    address: str,
    selector: str,
) -> Optional[str]:

    return await rpc_call(
        chain,
        "eth_call",
        [
            {
                "to": address,
                "data": selector,
            },
            "latest",
        ],
    )


# ============================================================
# TOKEN METADATA
# ============================================================

async def get_token_metadata(
    chain: Dict[str, Any],
    address: str,
) -> Dict[str, Any]:

    metadata = {
        "name": None,
        "symbol": None,
        "decimals": None,
    }

    # Alchemy token metadata first
    if ALCHEMY_API_KEY and chain.get("alchemy"):

        url = (
            f"https://{chain['alchemy']}.g.alchemy.com/v2/"
            f"{ALCHEMY_API_KEY}"
        )

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getTokenMetadata",
            "params": [address],
        }

        try:

            timeout_obj = aiohttp.ClientTimeout(total=15)

            async with aiohttp.ClientSession(
                timeout=timeout_obj
            ) as session:

                async with session.post(
                    url,
                    json=payload,
                ) as response:

                    if response.status == 200:

                        data = await response.json()

                        result = data.get("result", {})

                        metadata["name"] = result.get("name")
                        metadata["symbol"] = result.get("symbol")
                        metadata["decimals"] = result.get(
                            "decimals"
                        )

        except Exception:
            pass

    # Standard ERC-20 fallback
    if not metadata["name"]:

        result = await erc20_call(
            chain,
            address,
            "0x06fdde03",
        )

        metadata["name"] = decode_string(result)

    if not metadata["symbol"]:

        result = await erc20_call(
            chain,
            address,
            "0x95d89b41",
        )

        metadata["symbol"] = decode_string(result)

    if metadata["decimals"] is None:

        result = await erc20_call(
            chain,
            address,
            "0x313ce567",
        )

        try:
            if result:
                metadata["decimals"] = int(
                    result,
                    16,
                )
        except Exception:
            pass

    return metadata


# ============================================================
# BASIC ON-CHAIN DATA
# ============================================================

async def get_native_balance(
    chain: Dict[str, Any],
    address: str,
) -> Optional[float]:

    result = await rpc_call(
        chain,
        "eth_getBalance",
        [address, "latest"],
    )

    if not result:
        return None

    try:
        return int(result, 16) / 10**18
    except Exception:
        return None


async def get_transaction_count(
    chain: Dict[str, Any],
    address: str,
) -> Optional[int]:

    result = await rpc_call(
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
    chain: Dict[str, Any],
) -> Optional[int]:

    result = await rpc_call(
        chain,
        "eth_blockNumber",
        [],
    )

    if not result:
        return None

    try:
        return int(result, 16)
    except Exception:
        return None


# ============================================================
# BLOCKSCOUT
# ============================================================

async def blockscout_request(
    chain: Dict[str, Any],
    params: Dict[str, Any],
) -> Optional[Any]:

    # --------------------------------------------------------
    # Preferred path when a Blockscout key is supplied later.
    # --------------------------------------------------------

    if BLOCKSCOUT_API_KEY:

        chain_id = chain["chain_id"]

        url = (
            f"https://api.blockscout.com/"
            f"{chain_id}/api"
        )

        params = dict(params)
        params["apikey"] = BLOCKSCOUT_API_KEY

        data = await http_get(
            url,
            params=params,
        )

        if data is not None:
            return data

    # --------------------------------------------------------
    # Public chain-specific Blockscout instance.
    # --------------------------------------------------------

    base_url = chain.get("blockscout")

    if not base_url:
        return None

    return await http_get(
        base_url,
        params=params,
    )


async def get_blockscout_token(
    chain: Dict[str, Any],
    address: str,
) -> Optional[Dict[str, Any]]:

    data = await blockscout_request(
        chain,
        {
            "module": "token",
            "action": "getToken",
            "contractaddress": address,
        },
    )

    if not data:
        return None

    result = data.get("result")

    if isinstance(result, dict):
        return result

    return None


async def get_blockscout_holders(
    chain: Dict[str, Any],
    address: str,
    page: int = 1,
    offset: int = 10,
) -> Optional[List[Dict[str, Any]]]:

    data = await blockscout_request(
        chain,
        {
            "module": "token",
            "action": "getTokenHolders",
            "contractaddress": address,
            "page": page,
            "offset": offset,
        },
    )

    if not data:
        return None

    result = data.get("result")

    if isinstance(result, list):
        return result

    return None


def format_token_amount(
    raw_value: Any,
    decimals: Optional[int],
) -> str:

    try:

        value = int(str(raw_value))

        decimals = (
            decimals
            if decimals is not None
            else 18
        )

        amount = value / (10 ** decimals)

        if amount >= 1_000_000_000:
            return f"{amount:,.0f}"

        if amount >= 1_000_000:
            return f"{amount:,.2f}"

        if amount >= 1:
            return f"{amount:,.4f}"

        return f"{amount:.8f}"

    except Exception:
        return str(raw_value)


async def get_holder_intelligence(
    chain: Dict[str, Any],
    address: str,
    decimals: Optional[int],
) -> Dict[str, Any]:

    result = {
        "available": False,
        "total_supply": None,
        "holder_count": None,
        "holders": [],
    }

    # Token metadata from Blockscout
    token_info = await get_blockscout_token(
        chain,
        address,
    )

    if token_info:

        result["available"] = True

        result["total_supply"] = token_info.get(
            "totalSupply"
        )

        # Some Blockscout responses expose holder count
        # under additional fields depending on version.
        for key in (
            "holders",
            "holderCount",
            "holdersCount",
        ):

            if token_info.get(key) is not None:

                result["holder_count"] = token_info.get(
                    key
                )

                break

    # Top holders
    holders = await get_blockscout_holders(
        chain,
        address,
        page=1,
        offset=10,
    )

    if holders is not None:

        result["available"] = True
        result["holders"] = holders

    # Derive a count from returned holders only if the
    # explorer did not give us a total.
    if (
        result["holder_count"] is None
        and holders
    ):

        result["holder_count"] = len(holders)

    return result


# ============================================================
# DEXSCREENER
# ============================================================

async def get_market_data(
    chain: Dict[str, Any],
    token_address: str,
) -> List[Dict[str, Any]]:

    dex_chain_id = chain.get("dex_id")

    if not dex_chain_id:
        return []

    url = (
        f"https://api.dexscreener.com/tokens/v1/"
        f"{dex_chain_id}/{token_address}"
    )

    data = await http_get(url)

    if not isinstance(data, list):
        return []

    pairs = []

    for pair in data[:5]:

        pairs.append({
            "pair": (
                f"{pair.get('baseToken', {}).get('symbol', '?')}"
                f"/"
                f"{pair.get('quoteToken', {}).get('symbol', '?')}"
            ),
            "dex": pair.get("dexId"),
            "price_usd": pair.get("priceUsd"),
            "change_24h": (
                pair.get("priceChange", {}).get("h24")
            ),
            "liquidity": (
                pair.get("liquidity", {}).get("usd")
            ),
            "volume_24h": (
                pair.get("volume", {}).get("h24")
            ),
            "market_cap": pair.get("marketCap"),
            "fdv": pair.get("fdv"),
            "url": pair.get("url"),
        })

    return pairs


# ============================================================
# TOKEN ANALYSIS
# ============================================================

async def analyze_token(
    token_address: str,
) -> Dict[str, Any]:

    token_address = token_address.strip()

    if not ADDRESS_RE.match(token_address):

        return {
            "error": (
                "That doesn't look like a valid EVM "
                "contract address."
            )
        }

    # --------------------------------------------------------
    # Automatically find which supported EVM chain(s)
    # contain the contract.
    # --------------------------------------------------------

    matches = await discover_chains(
        token_address
    )

    if not matches:

        return {
            "error": (
                "I couldn't find a deployed contract at "
                f"{token_address} on the supported EVM "
                "networks."
            )
        }

    # Same address can legitimately exist on multiple chains.
    if len(matches) > 1:

        return {
            "multiple_chains": True,
            "address": token_address,
            "matches": [
                {
                    "key": key,
                    "name": EVM_CHAINS[key]["name"],
                    "chain_id": EVM_CHAINS[key]["chain_id"],
                }
                for key in matches
            ],
        }

    chain_key = matches[0]
    chain = EVM_CHAINS[chain_key]

    # --------------------------------------------------------
    # Collect data concurrently.
    # --------------------------------------------------------

    (
        metadata,
        native_balance,
        tx_count,
        latest_block,
        market_data,
        holder_data,
    ) = await asyncio.gather(

        get_token_metadata(
            chain,
            token_address,
        ),

        get_native_balance(
            chain,
            token_address,
        ),

        get_transaction_count(
            chain,
            token_address,
        ),

        get_latest_block(
            chain,
        ),

        get_market_data(
            chain,
            token_address,
        ),

        get_holder_intelligence(
            chain,
            token_address,
            None,
        ),
    )

    # Holder data needs decimals for readable amounts.
    holder_data = await get_holder_intelligence(
        chain,
        token_address,
        metadata.get("decimals"),
    )

    return {
        "address": token_address,
        "chain_key": chain_key,
        "chain": chain,
        "metadata": metadata,
        "native_balance": native_balance,
        "tx_count": tx_count,
        "latest_block": latest_block,
        "market_data": market_data,
        "holders": holder_data,
    }


# ============================================================
# FORMATTING
# ============================================================

def format_analysis(
    data: Dict[str, Any],
) -> str:

    if data.get("error"):
        return f"❌ {data['error']}"

    if data.get("multiple_chains"):

        lines = [
            "⚠️ This contract exists on multiple supported chains.",
            "",
            f"📜 Contract: {data['address']}",
            "",
            "Detected networks:",
        ]

        for item in data["matches"]:

            lines.append(
                f"• {item['name']} "
                f"(Chain ID {item['chain_id']})"
            )

        lines.extend([
            "",
            "Please provide the chain name with the address "
            "for this ambiguous case."
        ])

        return "\n".join(lines)

    metadata = data["metadata"]
    chain = data["chain"]

    name = metadata.get("name") or "Unknown Token"
    symbol = metadata.get("symbol") or "?"

    decimals = metadata.get("decimals")

    lines = [
        "🤖 Web3 Oasis — Token Analysis",
        "",
        f"🪙 {name} ({symbol})",
        f"⛓️ Chain: {chain['name']}",
        f"🆔 Chain ID: {chain['chain_id']}",
        f"📜 Contract: {data['address']}",
    ]

    if decimals is not None:
        lines.append(
            f"🔢 Decimals: {decimals}"
        )

    lines.extend([
        "",
        "💰 Native Balance: "
        + (
            f"{data['native_balance']:.6f} "
            f"{chain['native']}"
            if data["native_balance"] is not None
            else "Unavailable"
        ),
        "🔢 Transaction Count: "
        + (
            str(data["tx_count"])
            if data["tx_count"] is not None
            else "Unavailable"
        ),
        "🧱 Latest Block: "
        + (
            str(data["latest_block"])
            if data["latest_block"] is not None
            else "Unavailable"
        ),
    ])

    # --------------------------------------------------------
    # Blockscout holder intelligence
    # --------------------------------------------------------

    holder_data = data.get("holders", {})

    if holder_data.get("available"):

        lines.extend([
            "",
            "👥 Holder Intelligence",
        ])

        if holder_data.get("total_supply") is not None:

            lines.append(
                "• Total Supply: "
                + format_token_amount(
                    holder_data["total_supply"],
                    decimals,
                )
            )

        if holder_data.get("holder_count") is not None:

            lines.append(
                "• Holders: "
                + str(holder_data["holder_count"])
            )

        holders = holder_data.get(
            "holders",
            [],
        )

        if holders:

            lines.extend([
                "",
                "🏆 Top Holders",
            ])

            for index, holder in enumerate(
                holders[:5],
                start=1,
            ):

                holder_address = holder.get(
                    "address",
                    "Unknown",
                )

                amount = format_token_amount(
                    holder.get("value", 0),
                    decimals,
                )

                lines.append(
                    f"{index}. "
                    f"{holder_address[:6]}..."
                    f"{holder_address[-4:]} "
                    f"— {amount} {symbol}"
                )

    # --------------------------------------------------------
    # Market data
    # --------------------------------------------------------

    market_data = data.get(
        "market_data",
        [],
    )

    lines.extend([
        "",
        "📊 Market Data",
    ])

    if not market_data:

        lines.append(
            "• No DexScreener pair found."
        )

    else:

        for pair in market_data[:3]:

            lines.append(
                f"• Pair: {pair['pair']}"
            )

            if pair.get("dex"):
                lines.append(
                    f"  DEX: {pair['dex']}"
                )

            if pair.get("price_usd"):
                lines.append(
                    f"  Price: ${pair['price_usd']}"
                )

            if pair.get("change_24h") is not None:
                lines.append(
                    f"  24h Change: "
                    f"{pair['change_24h']}%"
                )

            if pair.get("liquidity"):
                lines.append(
                    f"  Liquidity: "
                    f"${pair['liquidity']}"
                )

            if pair.get("volume_24h"):
                lines.append(
                    f"  24h Volume: "
                    f"${pair['volume_24h']}"
                )

            if pair.get("market_cap"):
                lines.append(
                    f"  Market Cap: "
                    f"${pair['market_cap']}"
                )

            if pair.get("fdv"):
                lines.append(
                    f"  FDV: "
                    f"${pair['fdv']}"
                )

            if pair.get("url"):
                lines.append(
                    f"  🔗 {pair['url']}"
                )

    return "\n".join(lines)


# ============================================================
# HOLDER-ONLY REPORT
# ============================================================

def format_holders(
    data: Dict[str, Any],
) -> str:

    if data.get("error"):
        return f"❌ {data['error']}"

    if data.get("multiple_chains"):

        lines = [
            "⚠️ This contract exists on multiple "
            "supported chains.",
            "",
            f"📜 {data['address']}",
            "",
            "Detected:",
        ]

        for item in data["matches"]:

            lines.append(
                f"• {item['name']} "
                f"(Chain ID {item['chain_id']})"
            )

        return "\n".join(lines)

    metadata = data["metadata"]
    chain = data["chain"]
    holder_data = data.get("holders", {})

    name = metadata.get("name") or "Unknown Token"
    symbol = metadata.get("symbol") or "?"
    decimals = metadata.get("decimals")

    lines = [
        "👥 Web3 Oasis — Holder Intelligence",
        "",
        f"🪙 {name} ({symbol})",
        f"⛓️ {chain['name']}",
        f"📜 {data['address']}",
        "",
    ]

    if not holder_data.get("available"):

        lines.append(
            "⚠️ Holder intelligence is not currently "
            "available for this chain through Blockscout."
        )

        lines.append(
            "The token itself was detected successfully, "
            "but this explorer does not expose the holder "
            "endpoint we need."
        )

        return "\n".join(lines)

    if holder_data.get("total_supply") is not None:

        lines.append(
            "💰 Total Supply: "
            + format_token_amount(
                holder_data["total_supply"],
                decimals,
            )
            + f" {symbol}"
        )

    if holder_data.get("holder_count") is not None:

        lines.append(
            "👥 Holder Count: "
            + str(holder_data["holder_count"])
        )

    holders = holder_data.get(
        "holders",
        [],
    )

    if holders:

        lines.extend([
            "",
            "🏆 Top Holders",
        ])

        for index, holder in enumerate(
            holders[:10],
            start=1,
        ):

            holder_address = holder.get(
                "address",
                "Unknown",
            )

            amount = format_token_amount(
                holder.get("value", 0),
                decimals,
            )

            lines.append(
                f"{index}. "
                f"`{holder_address[:8]}..."
                f"{holder_address[-6:]}` "
                f"— {amount} {symbol}"
            )

    else:

        lines.append(
            "No holder records were returned."
        )

    return "\n".join(lines)