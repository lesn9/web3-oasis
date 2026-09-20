import os
import re
import logging
from typing import Any, Dict, Optional

import aiohttp


logger = logging.getLogger(__name__)

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")

# Alchemy Ethereum RPC endpoint
ETH_RPC_URL = (
    f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
    if ALCHEMY_API_KEY
    else None
)

DEXSCREENER_TOKEN_URL = (
    "https://api.dexscreener.com/latest/dex/tokens/"
)

ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")


def is_valid_address(address: str) -> bool:
    """Basic Ethereum address validation."""
    return bool(ADDRESS_PATTERN.match(address))


async def rpc_call(
    method: str,
    params: list,
) -> Optional[Any]:
    """Make an Ethereum JSON-RPC request through Alchemy."""

    if not ETH_RPC_URL:
        logger.warning("ALCHEMY_API_KEY is not configured.")
        return None

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    try:
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.post(
                ETH_RPC_URL,
                json=payload,
            ) as response:

                if response.status != 200:
                    logger.warning(
                        "Alchemy returned HTTP %s",
                        response.status,
                    )
                    return None

                data = await response.json()

                if "error" in data:
                    logger.warning(
                        "Alchemy RPC error: %s",
                        data["error"],
                    )
                    return None

                return data.get("result")

    except Exception as exc:
        logger.exception(
            "RPC request failed: %s",
            exc,
        )
        return None


async def get_native_balance(
    address: str,
) -> Optional[float]:
    """Get an address ETH balance."""

    if not is_valid_address(address):
        return None

    result = await rpc_call(
        "eth_getBalance",
        [address, "latest"],
    )

    if result is None:
        return None

    try:
        wei = int(result, 16)
        return wei / 10**18

    except (ValueError, TypeError):
        return None


async def get_transaction_count(
    address: str,
) -> Optional[int]:
    """Get the number of transactions sent by an address."""

    if not is_valid_address(address):
        return None

    result = await rpc_call(
        "eth_getTransactionCount",
        [address, "latest"],
    )

    if result is None:
        return None

    try:
        return int(result, 16)

    except (ValueError, TypeError):
        return None


async def get_token_market_data(
    token_address: str,
) -> Dict[str, Any]:
    """
    Get market information from DexScreener.

    This includes things such as:
    - price
    - liquidity
    - volume
    - market cap
    - pair information
    """

    if not is_valid_address(token_address):
        return {
            "success": False,
            "error": "Invalid Ethereum contract address.",
        }

    url = f"{DEXSCREENER_TOKEN_URL}{token_address}"

    try:
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(url) as response:

                if response.status != 200:
                    return {
                        "success": False,
                        "error": (
                            f"DexScreener returned HTTP "
                            f"{response.status}"
                        ),
                    }

                data = await response.json()

                pairs = data.get("pairs") or []

                if not pairs:
                    return {
                        "success": True,
                        "found": False,
                        "pairs": [],
                    }

                formatted_pairs = []

                for pair in pairs:

                    liquidity = pair.get("liquidity") or {}

                    formatted_pairs.append(
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
                            "liquidity_usd": liquidity.get(
                                "usd"
                            ),
                            "volume_24h": (
                                pair.get("volume") or {}
                            ).get("h24"),
                            "price_change_24h": (
                                pair.get("priceChange") or {}
                            ).get("h24"),
                            "base_token": (
                                pair.get("baseToken") or {}
                            ).get("symbol"),
                            "quote_token": (
                                pair.get("quoteToken") or {}
                            ).get("symbol"),
                        }
                    )

                return {
                    "success": True,
                    "found": True,
                    "pairs": formatted_pairs,
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


async def analyze_token(
    token_address: str,
) -> Dict[str, Any]:
    """
    Main analysis function.

    This combines the available on-chain and
    market data into one structured result.
    """

    token_address = token_address.strip()

    if not is_valid_address(token_address):
        return {
            "success": False,
            "error": (
                "That doesn't look like a valid "
                "Ethereum contract address."
            ),
        }

    market_data = await get_token_market_data(
        token_address
    )

    balance = await get_native_balance(
        token_address
    )

    tx_count = await get_transaction_count(
        token_address
    )

    result = {
        "success": True,
        "address": token_address,
        "native_balance_eth": balance,
        "transaction_count": tx_count,
        "market": market_data,
    }

    return result


def format_analysis(
    data: Dict[str, Any],
) -> str:
    """Turn analysis data into a Telegram-friendly message."""

    if not data.get("success"):
        return (
            "❌ Analysis failed.\n\n"
            f"{data.get('error', 'Unknown error')}"
        )

    address = data.get("address")

    balance = data.get(
        "native_balance_eth"
    )

    tx_count = data.get(
        "transaction_count"
    )

    market = data.get(
        "market",
        {},
    )

    lines = [
        "🔎 TOKEN INTELLIGENCE",
        "",
        f"📍 Contract:",
        f"`{address}`",
        "",
    ]

    if balance is not None:
        lines.extend(
            [
                f"💰 ETH balance: {balance:.6f} ETH",
            ]
        )
    else:
        lines.append(
            "💰 ETH balance: unavailable"
        )

    if tx_count is not None:
        lines.extend(
            [
                f"🧾 Transaction count: {tx_count}",
            ]
        )
    else:
        lines.append(
            "🧾 Transaction count: unavailable"
        )

    lines.append("")

    if market.get("success"):

        if not market.get("found"):
            lines.append(
                "📊 Market data: No DexScreener pairs found."
            )

        else:

            pairs = market.get(
                "pairs",
                [],
            )

            lines.append(
                f"📊 Market pairs found: {len(pairs)}"
            )

            # Show the first few pairs rather than
            # flooding the Telegram chat.
            for pair in pairs[:3]:

                symbol = pair.get(
                    "base_token"
                ) or "Unknown"

                price = pair.get(
                    "price_usd"
                )

                liquidity = pair.get(
                    "liquidity_usd"
                )

                volume = pair.get(
                    "volume_24h"
                )

                dex = pair.get(
                    "dex"
                ) or "Unknown"

                lines.extend(
                    [
                        "",
                        f"🔹 {symbol} / {dex}",
                        f"Price: ${price or 'N/A'}",
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
            "📊 Market data unavailable."
        )

    lines.extend(
        [
            "",
            "⚠️ This is raw intelligence data, "
            "not financial advice.",
        ]
    )

    return "\n".join(lines)