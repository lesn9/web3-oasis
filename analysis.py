import os
import asyncio
import logging
from typing import Any

import aiohttp


logger = logging.getLogger("web3-oasis.analysis")

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "").strip()
BLOCKSCOUT_API_KEY = os.getenv("BLOCKSCOUT_API_KEY", "").strip()


# ============================================================
# SUPPORTED CHAINS
# ============================================================

CHAINS = {
    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "native": "ETH",
        "alchemy": "eth-mainnet",
        "rpc": "https://eth.llamarpc.com",
    },
    "base": {
        "name": "Base",
        "chain_id": 8453,
        "native": "ETH",
        "alchemy": "base-mainnet",
        "rpc": "https://mainnet.base.org",
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "native": "ETH",
        "alchemy": "arb-mainnet",
        "rpc": "https://arb1.arbitrum.io/rpc",
    },
    "optimism": {
        "name": "Optimism",
        "chain_id": 10,
        "native": "ETH",
        "alchemy": "opt-mainnet",
        "rpc": "https://mainnet.optimism.io",
    },
    "polygon": {
        "name": "Polygon",
        "chain_id": 137,
        "native": "POL",
        "alchemy": "polygon-mainnet",
        "rpc": "https://polygon-rpc.com",
    },
    "bnb": {
        "name": "BNB Smart Chain",
        "chain_id": 56,
        "native": "BNB",
        "alchemy": None,
        "rpc": "https://bsc-dataseed.binance.org",
    },
    "avalanche": {
        "name": "Avalanche",
        "chain_id": 43114,
        "native": "AVAX",
        "alchemy": "avax-mainnet",
        "rpc": "https://api.avax.network/ext/bc/C/rpc",
    },
    "linea": {
        "name": "Linea",
        "chain_id": 59144,
        "native": "ETH",
        "alchemy": "linea-mainnet",
        "rpc": "https://rpc.linea.build",
    },
    "zksync": {
        "name": "zkSync Era",
        "chain_id": 324,
        "native": "ETH",
        "alchemy": "zksync-mainnet",
        "rpc": "https://mainnet.era.zksync.io",
    },
    "scroll": {
        "name": "Scroll",
        "chain_id": 534352,
        "native": "ETH",
        "alchemy": "scroll-mainnet",
        "rpc": "https://rpc.scroll.io",
    },
    "mantle": {
        "name": "Mantle",
        "chain_id": 5000,
        "native": "MNT",
        "alchemy": "mantle-mainnet",
        "rpc": "https://rpc.mantle.xyz",
    },
    "blast": {
        "name": "Blast",
        "chain_id": 81457,
        "native": "ETH",
        "alchemy": "blast-mainnet",
        "rpc": "https://rpc.blast.io",
    },
    "gnosis": {
        "name": "Gnosis",
        "chain_id": 100,
        "native": "xDAI",
        "alchemy": None,
        "rpc": "https://rpc.gnosischain.com",
    },
    "celo": {
        "name": "Celo",
        "chain_id": 42220,
        "native": "CELO",
        "alchemy": None,
        "rpc": "https://forno.celo.org",
    },
    "unichain": {
        "name": "Unichain",
        "chain_id": 130,
        "native": "ETH",
        "alchemy": "unichain-mainnet",
        "rpc": "https://mainnet.unichain.org",
    },
    "world": {
        "name": "World Chain",
        "chain_id": 480,
        "native": "ETH",
        "alchemy": "worldchain-mainnet",
        "rpc": "https://worldchain-mainnet.g.alchemy.com/public",
    },
    "soneium": {
        "name": "Soneium",
        "chain_id": 1868,
        "native": "ETH",
        "alchemy": None,
        "rpc": "https://rpc.soneium.org",
    },
    "shape": {
        "name": "Shape",
        "chain_id": 360,
        "native": "ETH",
        "alchemy": None,
        "rpc": "https://mainnet.shape.network",
    },
    "sonic": {
        "name": "Sonic",
        "chain_id": 146,
        "native": "S",
        "alchemy": None,
        "rpc": "https://rpc.soniclabs.com",
    },
    "berachain": {
        "name": "Berachain",
        "chain_id": 80094,
        "native": "BERA",
        "alchemy": "berachain-mainnet",
        "rpc": "https://rpc.berachain.com",
    },
    "monad": {
        "name": "Monad",
        "chain_id": 143,
        "native": "MON",
        "alchemy": "monad-mainnet",
        "rpc": "https://rpc.monad.xyz",
    },
    "robinhood": {
        "name": "Robinhood Chain",
        "chain_id": 4663,
        "native": "ETH",
        "alchemy": "robinhood-mainnet",
        "rpc": "https://rpc.mainnet.chain.robinhood.com",
    },
    "arc": {
        "name": "Arc",
        "chain_id": 5042,
        "native": "USDC",
        "alchemy": "arc-mainnet",
        "rpc": "https://rpc.arc.network",
    },
    "ink": {
        "name": "Ink",
        "chain_id": 57073,
        "native": "ETH",
        "alchemy": "ink-mainnet",
        "rpc": "https://rpc-gel.inkonchain.com",
    },
    "abstract": {
        "name": "Abstract",
        "chain_id": 2741,
        "native": "ETH",
        "alchemy": "abstract-mainnet",
        "rpc": "https://api.mainnet.abs.xyz",
    },
}


# ============================================================
# HTTP HELPERS
# ============================================================

async def http_get(
    url: str,
    params: dict | None = None,
    timeout: int = 20,
) -> Any:
    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(
                        "GET %s returned HTTP %s",
                        url,
                        response.status,
                    )
                    return None

                return await response.json(content_type=None)

    except Exception as exc:
        logger.warning("GET failed %s: %s", url, exc)
        return None


async def rpc_call(
    chain: dict,
    method: str,
    params: list,
) -> Any:

    urls = []

    alchemy_network = chain.get("alchemy")

    if ALCHEMY_API_KEY and alchemy_network:
        urls.append(
            f"https://{alchemy_network}.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
        )

    public_rpc = chain.get("rpc")

    if public_rpc:
        urls.append(public_rpc)

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    timeout_obj = aiohttp.ClientTimeout(total=15)

    for url in urls:
        try:
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.post(url, json=payload) as response:

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
# CHAIN DETECTION
# ============================================================

async def check_chain(address: str, chain_key: str) -> dict | None:

    chain = CHAINS[chain_key]

    code = await rpc_call(
        chain,
        "eth_getCode",
        [address, "latest"],
    )

    if code is None:
        return None

    if code == "0x":
        return None

    return chain


async def detect_chain(address: str) -> tuple[str, dict] | None:

    address = address.strip()

    tasks = [
        check_chain(address, key)
        for key in CHAINS
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    for key, result in zip(CHAINS.keys(), results):

        if isinstance(result, dict):
            return key, result

    return None


# ============================================================
# ERC20 CALL HELPERS
# ============================================================

def encode_address(address: str) -> str:
    return address.lower().replace("0x", "").rjust(64, "0")


def decode_string(result: str | None) -> str | None:

    if not result or result == "0x":
        return None

    try:
        data = bytes.fromhex(result[2:])

        if len(data) >= 64:

            offset = int.from_bytes(data[:32], "big")

            if offset + 32 <= len(data):
                length = int.from_bytes(
                    data[offset:offset + 32],
                    "big",
                )

                start = offset + 32
                end = start + length

                if end <= len(data):
                    return data[start:end].decode(
                        "utf-8",
                        errors="ignore",
                    )

        return bytes.fromhex(
            result[2:]
        ).decode(
            "utf-8",
            errors="ignore",
        ).rstrip("\x00")

    except Exception:
        return None


async def erc20_call(
    chain: dict,
    address: str,
    selector: str,
) -> str | None:

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


async def get_token_metadata(
    chain: dict,
    address: str,
) -> dict:

    name_result, symbol_result, decimals_result = await asyncio.gather(
        erc20_call(chain, address, "0x06fdde03"),
        erc20_call(chain, address, "0x95d89b41"),
        erc20_call(chain, address, "0x313ce567"),
    )

    name = decode_string(name_result) or "Unknown Token"
    symbol = decode_string(symbol_result) or "UNKNOWN"

    decimals = 18

    try:
        if decimals_result and decimals_result != "0x":
            decimals = int(decimals_result, 16)
    except Exception:
        decimals = 18

    return {
        "name": name.strip() or "Unknown Token",
        "symbol": symbol.strip() or "UNKNOWN",
        "decimals": decimals,
    }


# ============================================================
# BLOCKCHAIN DATA
# ============================================================

async def get_native_balance(
    chain: dict,
    address: str,
) -> float:

    result = await rpc_call(
        chain,
        "eth_getBalance",
        [address, "latest"],
    )

    if not result:
        return 0.0

    try:
        return int(result, 16) / 10**18
    except Exception:
        return 0.0


async def get_transaction_count(
    chain: dict,
    address: str,
) -> int:

    result = await rpc_call(
        chain,
        "eth_getTransactionCount",
        [address, "latest"],
    )

    if not result:
        return 0

    try:
        return int(result, 16)
    except Exception:
        return 0


async def get_latest_block(chain: dict) -> int:

    result = await rpc_call(
        chain,
        "eth_blockNumber",
        [],
    )

    if not result:
        return 0

    try:
        return int(result, 16)
    except Exception:
        return 0


# ============================================================
# BLOCKSCOUT V2
# ============================================================

def blockscout_base(chain: dict) -> str:
    return (
        f"https://api.blockscout.com/"
        f"{chain['chain_id']}/api/v2"
    )


async def blockscout_v2(
    chain: dict,
    path: str,
    params: dict | None = None,
) -> Any:

    if not BLOCKSCOUT_API_KEY:
        return None

    url = blockscout_base(chain) + path

    request_params = dict(params or {})
    request_params["apikey"] = BLOCKSCOUT_API_KEY

    return await http_get(
        url,
        params=request_params,
        timeout=25,
    )


async def get_blockscout_token(
    chain: dict,
    address: str,
) -> dict | None:

    return await blockscout_v2(
        chain,
        f"/tokens/{address}",
    )


async def get_blockscout_counters(
    chain: dict,
    address: str,
) -> dict | None:

    return await blockscout_v2(
        chain,
        f"/tokens/{address}/counters",
    )


async def get_holder_page(
    chain: dict,
    address: str,
    cursor: dict | None = None,
) -> dict:

    params = dict(cursor or {})

    # Ask Blockscout for 10 records per page.
    # Blockscout cursor responses include items_count,
    # which is carried into the next cursor automatically.
    params["items_count"] = 10

    data = await blockscout_v2(
        chain,
        f"/tokens/{address}/holders",
        params=params,
    )

    if not data:
        return {
            "items": [],
            "next_page_params": None,
        }

    items = data.get("items") or []

    return {
        "items": items,
        "next_page_params": data.get("next_page_params"),
    }


def holder_address(holder: dict) -> str:

    value = holder.get("address")

    if isinstance(value, dict):
        return (
            value.get("hash")
            or value.get("address")
            or "Unknown"
        )

    if isinstance(value, str):
        return value

    value = holder.get("address_hash")

    if value:
        return value

    return "Unknown"


def holder_raw_value(holder: dict) -> int:

    value = (
        holder.get("value")
        or holder.get("balance")
        or holder.get("token_balance")
        or "0"
    )

    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return 0


async def get_holder_intelligence(
    chain: dict,
    address: str,
    decimals: int,
) -> dict:

    token_data, counters, first_page = await asyncio.gather(
        get_blockscout_token(chain, address),
        get_blockscout_counters(chain, address),
        get_holder_page(chain, address),
    )

    total_supply_raw = None
    total_holder_count = None

    if token_data:
        total_supply_raw = (
            token_data.get("total_supply")
            or token_data.get("totalSupply")
        )

    if counters:
        total_holder_count = (
            counters.get("holders_count")
            or counters.get("holder_count")
            or counters.get("token_holders_count")
            or counters.get("holders")
        )

    total_supply = None

    try:
        if total_supply_raw is not None:
            total_supply = int(total_supply_raw) / (
                10 ** decimals
            )
    except Exception:
        total_supply = None

    try:
        if total_holder_count is not None:
            total_holder_count = int(total_holder_count)
    except Exception:
        total_holder_count = None

    return {
        "total_supply": total_supply,
        "holder_count": total_holder_count,
        "first_page": first_page,
    }


# ============================================================
# DEXSCREENER
# ============================================================

async def get_market_data(
    address: str,
    chain: dict,
) -> dict | None:

    url = (
        "https://api.dexscreener.com/"
        f"latest/dex/tokens/{address}"
    )

    data = await http_get(
        url,
        timeout=20,
    )

    if not data:
        return None

    pairs = data.get("pairs") or []

    if not pairs:
        return None

    chain_id = str(chain["chain_id"])
    chain_name = chain["name"].lower()

    matching = []

    for pair in pairs:

        pair_chain = str(
            pair.get("chainId", "")
        ).lower()

        if (
            pair_chain == chain_id
            or pair_chain == chain_name
            or pair_chain in (
                chain_name.replace(" ", ""),
                chain_name.replace(" ", "-"),
            )
        ):
            matching.append(pair)

    if not matching:
        matching = pairs

    pair = matching[0]

    return {
        "pair": (
            f"{pair.get('baseToken', {}).get('symbol', '?')}/"
            f"{pair.get('quoteToken', {}).get('symbol', '?')}"
        ),
        "dex": pair.get("dexId") or "Unknown",
        "price": pair.get("priceUsd"),
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
    }


# ============================================================
# MAIN ANALYSIS
# ============================================================

async def analyze_token(address: str) -> dict:

    address = address.strip()

    if not address.startswith("0x") or len(address) != 42:
        raise ValueError("Invalid EVM contract address.")

    detected = await detect_chain(address)

    if not detected:
        raise ValueError(
            "Could not identify the blockchain for that contract."
        )

    chain_key, chain = detected

    metadata_task = get_token_metadata(
        chain,
        address,
    )

    balance_task = get_native_balance(
        chain,
        address,
    )

    tx_task = get_transaction_count(
        chain,
        address,
    )

    block_task = get_latest_block(
        chain,
    )

    market_task = get_market_data(
        address,
        chain,
    )

    metadata, balance, tx_count, latest_block, market = (
        await asyncio.gather(
            metadata_task,
            balance_task,
            tx_task,
            block_task,
            market_task,
        )
    )

    holder_data = await get_holder_intelligence(
        chain,
        address,
        metadata["decimals"],
    )

    return {
        "address": address,
        "chain_key": chain_key,
        "chain": chain,
        "metadata": metadata,
        "native_balance": balance,
        "transaction_count": tx_count,
        "latest_block": latest_block,
        "market": market,
        "holders": holder_data,
    }


# ============================================================
# FORMATTING
# ============================================================

def format_number(value: Any, decimals: int = 2) -> str:

    if value is None:
        return "N/A"

    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return str(value)


def format_analysis(data: dict) -> str:

    metadata = data["metadata"]
    chain = data["chain"]
    market = data.get("market")

    lines = [
        "🤖 Web3 Oasis — Token Analysis",
        "",
        f"🪙 {metadata['name']} ({metadata['symbol']})",
        f"⛓️ Chain: {chain['name']}",
        f"🆔 Chain ID: {chain['chain_id']}",
        f"📜 Contract: {data['address']}",
        f"🔢 Decimals: {metadata['decimals']}",
        "",
        (
            f"💰 Native Balance: "
            f"{format_number(data['native_balance'], 6)} "
            f"{chain['native']}"
        ),
        f"🔢 Transaction Count: {data['transaction_count']}",
        f"🧱 Latest Block: {data['latest_block']}",
        "",
        "📊 Market Data",
    ]

    if not market:
        lines.append("• No DexScreener pair found.")

    else:
        lines.extend([
            f"• Pair: {market.get('pair', 'N/A')}",
            f"  DEX: {market.get('dex', 'N/A')}",
            f"  Price: ${market.get('price', 'N/A')}",
            f"  24h Change: {market.get('change_24h', 'N/A')}%",
            f"  Liquidity: ${format_number(market.get('liquidity'))}",
            f"  24h Volume: ${format_number(market.get('volume_24h'))}",
            f"  Market Cap: ${format_number(market.get('market_cap'), 0)}",
            f"  FDV: ${format_number(market.get('fdv'), 0)}",
        ])

        if market.get("url"):
            lines.append(
                f"  🔗 {market['url']}"
            )

    return "\n".join(lines)


def format_holder_page(
    data: dict,
    page_items: list,
    page_number: int,
    has_previous: bool,
    has_next: bool,
) -> str:

    metadata = data["metadata"]
    chain = data["chain"]
    holders = data["holders"]

    total_supply = holders.get("total_supply")
    holder_count = holders.get("holder_count")

    lines = [
        "👥 Web3 Oasis — Holder Intelligence",
        "",
        f"🪙 {metadata['name']} ({metadata['symbol']})",
        f"⛓️ {chain['name']}",
        f"📜 {data['address']}",
        "",
        (
            f"💰 Total Supply: "
            f"{format_number(total_supply)} "
            f"{metadata['symbol']}"
        ),
    ]

    if holder_count is not None:
        lines.append(
            f"👥 Holder Count: {holder_count:,}"
        )
    else:
        lines.append(
            "👥 Holder Count: Unavailable"
        )

    lines.extend([
        "",
        f"🏆 Top Holders — Page {page_number}",
        "",
    ])

    if not page_items:
        lines.append("No holder records were returned.")
        return "\n".join(lines)

    for index, holder in enumerate(page_items, start=1):

        address = holder_address(holder)

        raw_value = holder_raw_value(holder)

        try:
            amount = raw_value / (
                10 ** metadata["decimals"]
            )
        except Exception:
            amount = 0

        if len(address) > 18:
            display_address = (
                f"{address[:10]}..."
                f"{address[-6:]}"
            )
        else:
            display_address = address

        lines.append(
            f"{index}. {display_address} — "
            f"{amount:,.2f} {metadata['symbol']}"
        )

    lines.extend([
        "",
        "Use the buttons below to browse more holders.",
    ])

    return "\n".join(lines)


def format_holders(data: dict) -> str:

    first_page = data["holders"]["first_page"]

    return format_holder_page(
        data=data,
        page_items=first_page.get("items", []),
        page_number=1,
        has_previous=False,
        has_next=bool(
            first_page.get("next_page_params")
        ),
    )