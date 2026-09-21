import os, asyncio, re, time, aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=20)
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

EVM_CHAINS = {
    1:("Ethereum","ethereum","https://eth-mainnet.g.alchemy.com/v2/{key}","https://eth.llamarpc.com"),
    8453:("Base","base","https://base-mainnet.g.alchemy.com/v2/{key}","https://base.llamarpc.com"),
    42161:("Arbitrum One","arbitrum","https://arb-mainnet.g.alchemy.com/v2/{key}","https://arbitrum.llamarpc.com"),
    10:("Optimism","optimism","https://opt-mainnet.g.alchemy.com/v2/{key}","https://optimism.llamarpc.com"),
    137:("Polygon","polygon","https://polygon-mainnet.g.alchemy.com/v2/{key}","https://polygon.llamarpc.com"),
    56:("BNB Smart Chain","bsc",None,"https://bsc-dataseed.binance.org"),
    43114:("Avalanche C-Chain","avalanche","https://avax-mainnet.g.alchemy.com/v2/{key}","https://api.avax.network/ext/bc/C/rpc"),
    59144:("Linea","linea","https://linea-mainnet.g.alchemy.com/v2/{key}","https://rpc.linea.build"),
    324:("zkSync Era","zksync","https://zksync-mainnet.g.alchemy.com/v2/{key}","https://mainnet.era.zksync.io"),
    534352:("Scroll","scroll",None,"https://rpc.scroll.io"),
    5000:("Mantle","mantle",None,"https://rpc.mantle.xyz"),
    81457:("Blast","blast",None,"https://rpc.blast.io"),
    100:("Gnosis","gnosis",None,"https://rpc.gnosischain.com"),
    42220:("Celo","celo",None,"https://forno.celo.org"),
    130:("Unichain","unichain",None,"https://mainnet.unichain.org"),
    480:("World Chain","worldchain","https://worldchain-mainnet.g.alchemy.com/v2/{key}","https://worldchain-mainnet.g.alchemy.com/v2/demo"),
    1868:("Soneium","soneium","https://soneium-mainnet.g.alchemy.com/v2/{key}","https://rpc.soneium.org"),
    360:("Shape","shape","https://shape-mainnet.g.alchemy.com/v2/{key}","https://mainnet.shape.network"),
    146:("Sonic","sonic","https://sonic-mainnet.g.alchemy.com/v2/{key}","https://rpc.soniclabs.com"),
    80094:("Berachain","berachain","https://berachain-mainnet.g.alchemy.com/v2/{key}","https://rpc.berachain.com"),
    143:("Monad","monad","https://monad-mainnet.g.alchemy.com/v2/{key}","https://rpc.monad.xyz"),
    1329:("Sei EVM","sei","https://sei-mainnet.g.alchemy.com/v2/{key}","https://evm-rpc.sei-apis.com"),
    7777777:("Zora","zora",None,"https://rpc.zora.energy"),
    204:("opBNB","opbnb","https://opbnb-mainnet.g.alchemy.com/v2/{key}","https://opbnb-mainnet-rpc.bnbchain.org"),
    1088:("Metis","metis",None,"https://andromeda.metis.io/?owner=1088"),
    33139:("ApeChain","apechain","https://apechain-mainnet.g.alchemy.com/v2/{key}","https://rpc.apechain.com/http"),
    34443:("Mode","mode",None,"https://mainnet.mode.network"),
    1284:("Moonbeam","moonbeam",None,"https://rpc.api.moonbeam.network"),
    4663:("Robinhood Chain","robinhood","https://robinhood-mainnet.g.alchemy.com/v2/{key}","https://rpc.mainnet.chain.robinhood.com"),
    1243:("Arc","arc","https://arc-mainnet.g.alchemy.com/v2/{key}","https://rpc.arc.network"),
    57073:("Ink","ink","https://ink-mainnet.g.alchemy.com/v2/{key}","https://rpc-gel.inkonchain.com"),
    2741:("Abstract","abstract","https://abstract-mainnet.g.alchemy.com/v2/{key}","https://api.mainnet.abs.xyz"),
}

EVM_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
SOL_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
SUI_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
TRON_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
TON_RE = re.compile(r"^(EQ|U               Q)[A-Za-z0-9_-]{46}$")
SELECTORS = {"name":"0x06fdde03","symbol":"0x95d89b41","decimals":"0x313ce567","totalSupply":"0x18160ddd"}

HOLDER_CACHE = {}
CACHE_TTL = 600
BLOCKVISION_BASE = "https://api.blockvision.org/v2/sui"


def short_address(a, l=10, r=8):
    return a if len(a) <= l+r+3 else f"{a[:l]}...{a[-r:]}"


def fmt_number(v):
    try:
        v = float(v)
    except:
        return str(v)
    for d, s in ((1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
        if abs(v) >= d:
            return f"{v/d:.2f}{s}"
    return f"{v:.2f}"


def detect_address_family(a):
    if EVM_RE.fullmatch(a): return "evm"
    if TRON_RE.fullmatch(a): return "tron"
    if TON_RE.fullmatch(a): return "ton"
    if SUI_RE.fullmatch(a) or ("::" in a and a.startswith("0x")): return "sui"
    if SOL_RE.fullmatch(a): return "solana"
    return "unknown"


async def http_json(s, method, url, **kw):
    try:
        async with s.request(method, url, timeout=TIMEOUT, **kw) as r:
            text = await r.text()
            if r.status != 200:
                return {"__http_error__": r.status, "__text__": text[:1200]}
            try:
                return await r.json(content_type=None)
            except:
                return None
    except Exception:
        return None


async def rpc(s, url, method, params):
    d = await http_json(s, "POST", url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if not d or d.get("error"):
        return None
    return d.get("result")


def alchemy_url(chain_id):
    key = os.getenv("ALCHEMY_API_KEY", "").strip()
    if not key:
        return None
    c = EVM_CHAINS[chain_id]
    return c[2].format(key=key) if c[2] else None


async def detect_evm(a):
    key = os.getenv("ALCHEMY_API_KEY", "").strip()
    async with aiohttp.ClientSession() as s:
        async def probe(cid, c):
            name, v slug, alchemy, public = c
            ur =ls = ([alchemy.format(key=key)] if al (chemy and key else []) + ([public] ifsupp public else [])
            for u in urlsly:
                code = await rpc(s, u, "eth_getCode", [a, "latest"])
                if code and code != "0x":
                    return {"chain_id": cid, "name": name, "slug": slug}
            return None
        out = await asyncio.gather(*(probe(cid, c) for cid, c in EVM_CHAINS.items()), return_exceptions=True)
    return [x for x in out if isinstance(x, dict)]


def dec_uint(x):
    try:
        return int(x, 16)
    except:
        return 0


def dec_string(x):
    try:
        h = x[2:]
        if len(h) >= 128:
            off = int(h[:64], 16) * 2
            if off + 64 <= len(h):
                n = int(h[off:off+64], 16)
                raw = h[off+64:off+64+n*2]
                return bytes.fromhex(raw).decode(errors="ignore").strip()
        return bytes.fromhex(h).decode(errors="ignore").strip("\x00").strip()
    except:
        return ""


async def evm_token(a, c):
    key = os.getenv("ALCHEMY_API_KEY", "").strip()
    _, _, alchemy, public = EVM_CHAINS[c["chain_id"]]
    urls = ([alchemy.format(key=key)] if alchemy and key else []) + ([public] if public else [])
    last = "RPC unavailable"
    for u in urls:
        try:
            async with aiohttp.ClientSession() as s:
                vals = await asyncio.gather(*(rpc(s, u, "eth_call", [{"to": a, "data": sel}, "latest"]) for sel in SELECTORS.values()))
            name, sym, dec, sup = vals
            d = dec_uint(dec)
            supply = dec_uint(sup) / (10**d if d < 78 else 1)
            return {"family": "evm", "chain": c["name"], "chain_id": c["chain_id"], "slug": c["slug"], "contract": a,
                    "name": dec_string(name) or "Unknown Token", "symbol": dec_string(sym) or "???",
                    "decimals": d, "total_supply": supply}
        except Exception as e:
            last = str(e)
    raise RuntimeError(last)


def normalize_transfer_value(t):
    raw = ((t.get("rawContract") or {}).get("value"))
    if isinstance(raw, str) and raw.startswith("0x"):
        try:
            return int(raw, 16)
        except:
            pass
    v = t.get("value")
    try:
        return int(round(float(v) * 10**18))
    except:
        return 0


async def compute_evm_holders(a, c):
    key = (c["chain_id"], a.lower())
    cached = HOLDER_CACHE.get(key)
    if cached and time.time() - cached["time"] < CACHE_TTL:
        return cached["data"]

    url = alchemy_url(c["chain_id"])
    if not url:
        raise RuntimeError("Alchemy key required for EVM holder scan.")

    transfers = None
    page_key = None
    source = "Alchemy Transfer API"
    max_pages = 500

    async with aiohttp.ClientSession() as s:
        for _ in range(max_pages):
            params = {
                "fromBlock": "0x0", "toBlock": "latest",
                "contractAddresses": [a], "category": ["erc20"],
                "excludeZeroValue": False, "maxCount": "0x3e8",
            }
            if page_key:
                params["pageKey"] = page_key
            d = await rpc(s, url, "alchemy_getAssetTransfers", [params])
            if d is None:
                page_key = None
                transfers = None
                continue
            if transfers is None:
                transfers = []
            batch = d.get("transfers", [])
            transfers.extend(batch)
            page_key = d.get("pageKey")
            if not page_key:
                break

    if transfers is None:
        transfers = await logs_transfers(a, c["chain_id"])
        source = "ERC-20 Transfer logs"
    if transfers is None:
        raise RuntimeError("No indexed ERC-20 transfer history available from Alchemy for this chain.")

    balances = {}
    for t in transfers:
        frm = t.get("from")
        to = t.get("to")
        if not frm or not to:
            continue
        value = normalize_transfer_value(t)
        frm = frm.lower()
        to = to.lower()
        balances[frm] = balances.get(frm, 0) - value
        balances[to] = balances.get(to, 0) + value

    meta = await evm_token(a, c)
    decimals = meta["decimals"]
    scale = 10**decimals
    holders = [(addr, bal) for addr, bal in balances.items() if bal > 0]
    holders.sort(key=lambda x: x[1], reverse=True)
    rows = [{"address": addr, "raw": bal, "value": bal / scale} for addr, bal in holders]

    data = {"items": rows, "total": len(rows), "source": source, "transfers": len(transfers), "meta": meta}
    HOLDER_CACHE[key] = {"time": time.time(), "data": data}
    return data


async def logs_transfers(a, cid):
    c = EVM_CHAINS[cid]
    key = os.getenv("ALCHEMY_API_KEY", "").strip()
    urls = ([c[2].format(key=key)] if c[2] and key else []) + ([c[3]] if c[3] else [])
    for url in urls:
        async with aiohttp.ClientSession() as s:
            latest = await rpc(s, url, "eth_blockNumber", [])
            if latest is None:
                continue
            hi = int(latest, 16)
            step = 100000
            logs = []
            start = 0
            while start <= hi:
                end = min(hi, start + step - 1)
                flt = {"fromBlock": hex(start), "toBlock": hex(end), "address": a, "topics": [TRANSFER_TOPIC]}
                d = await rpc(s, url, "eth_getLogs", [flt])
                if d is None:
                    if step > 5000:
                        step //= 2
                        continue
                    start = end + 1
                    continue
                logs.extend(d)
                start = end + 1
                if len(logs) > 200000:
                    raise RuntimeError("Token has too many Transfer events for an on-demand holder scan.")
            out = []
            for lg in logs:
                topics = lg.get("topics", [])
                if len(topics) < 3:
                    continue
                frm = "0x" + topics[1][-40:]
                to = "0x" + topics[2][-40:]
                raw = lg.get("data", "0x")
                try:
                    value = int(raw, 16)
                except:
                    continue
                out.append({"from": frm, "to": to, "raw_value": value, "value": value / 1e18})
            return out
    return None


async def solana_token(a):
    key = os.getenv("ALCHEMY_API_KEY", "").strip()
    urls = []
    if key:
        urls.append(f"https://solana-mainnet.g.alchemy.com/v2/{key}")
    urls.append("https://api.mainnet-beta.solana.com")

    last = "Solana RPC unavailable"
    for u in urls:
        try:
            async with aiohttp.ClientSession() as s:
                asset = await rpc(s, u, "getAsset", [a, {"displayOptions": {"showFungible": True}}])
                accounts = []
                total = 0
                cursor = None
                for _ in range(50):
                    params = {"mint": a, "limit": 1000}
                    if cursor:
                        params["cursor"] = cursor
                    d = await rpc(s, u, "getTokenAccounts", [params])
                    if not d:
                        break
                    total = d.get("total", total)
                    batch = d.get("token_accounts", [])
                    accounts.extend(batch)
                    cursor = d.get("cursor")
                    if not cursor or not batch:
                        break

                supply = await rpc(s, u, "getTokenSupply", [a])
 or {}).get("value", {})
                dec = int(v.get("decimals", 0))
                raw = int(v.get("amount", "0"))

                content = ((asset or {}).get("content") or {})
                md = content.get("metadata") or {}

                rows = []
                for acct in accounts:
                    pubkey = acct.get("pubkey") or acct.get("address") or ""
                    owner = ((acct.get("account") or {}).get("owner")) or acct.get("owner") or ""
                    amount = acct.get("uiAmount") or acct.get("amount") or acct.get("uiAmountString") or "0"
                    rows.append({"address": pubkey, "owner": owner, "value": amount})

                return {
                    "family": "solana", "chain": "Solana", "contract": a,
                    "name": md.get("name") or "SPL Token",
                    "symbol": md.get("symbol") or "",
                    "decimals": dec,
                    "total_supply": raw / (10**dec if dec else 1),
                    "top_accounts": rows[:20],
                    "holders": rows,
                    "total_holders": total,
                    "note": "Real token accounts from Alchemy getTokenAccounts."
                }
        except Exception as e:
            last = str(e)
    raise RuntimeError(last)


SUI_RPC = "https://fullnode.mainnet.sui.io:443"


async def sui_rpc(method, params):
    async with aiohttp.ClientSession() as s:
        return await rpc(s, SUI_RPC, method, params)


async def sui_resolve_coin_type(a):
    if "::" in a:
        return a
    obj = await sui_rpc("sui_getObject", [a, {"showType": True, "showContent": True, "showOwner": True}])
    typ = ((obj or {}).get("data") or {}).get("type") or ""
    m = re.search(r"(?:0x2::coin::Coin|0x2::coin::CoinMetadata)<(.+)>$", typ)
    if m:
        return m.group(1)
    raise RuntimeError("That Sui address is an object ID, not a coin type. Send the full coin type, e.g. 0x...::module::TOKEN.")


async def sui_token(a):
    coin_type = await sui_resolve_coin_type(a)
    key = os.getenv("BLOCKVISION_API_KEY", "").strip()
    if not key:
        raise RuntimeError("BLOCKVISION_API_KEY is not set. Sui metadata requires BlockVision.")

    async with aiohttp.ClientSession() as s:
        d = await http_json(
            s, "GET", f"{BLOCKVISION_BASE}/coin/detail",
            params={"coinType": coin_type},
            headers={"x-api-key": key, "accept": "application/json"}
        )
    if not isinstance(d, dict) or d.get("__http_error__"):
        raise RuntimeError(f"BlockVision detail failed: {str(d)[:400]}")

    data = d.get("data") or d
    decimals = int(data.get("decimals") or 0)
    total_supply_raw = data.get("totalSupply") or data.get("supply") or 0
    try:
        total_supply = float(total_supply_raw) / (10 ** decimals) if decimals else float(total_supply_raw)
    except:
        total_supply = 0.0

    return {
        "family": "sui", "chain": "Sui", "contract": coin_type, "input": a,
        "name": data.get("name") or "Unknown Sui Coin",
        "symbol": data.get("symbol") or "???",
        "decimals": decimals,
        "total_supply": total_supply,
        "total_holders": data.get("holders") or data.get("holderCount"),
        "coin_type": coin_type,
    }


async def sui_holders(a):
    coin_type = await sui_resolve_coin_type(a)
    key = os.getenv("BLOCKVISION_API_KEY", "").strip()
    if not key:
        return {"coin_type": coin_type, "items": [], "total": None, "needs_key": True}

    all_rows = []
    cursor = None
    async with aiohttp.ClientSession() as s:
        for _ in range(200):
            params = {"coinType": coin_type, "limit": 50}
            if cursor:
                params["cursor"] = cursor
            d = await http_json(
                s, "GET", f"{BLOCKVISION_BASE}/coin/holders",
                params=params,
                headers={"x-api-key": key, "accept": "application/json"}
            )
            if not isinstance(d, dict) or d.get("__http_error__"):
                break
            payload = d.get("data") or d
            rows = payload.get("data") or payload.get("holders") or []
            all_rows.extend(rows)
            cursor = payload.get("nextPageCursor") or payload.get("cursor")
            if not cursor or not rows:
                break

    items = []
    for x in all_rows:
        addr = x.get("address") or x.get("holderAddress") or x.get("owner") or ""
        if addr:
            items.append({
                "address": addr,
                "value": x.get("quantity") or x.get("balance") or x.get("amount") or "0",
                "percentage": x.get("percentage"),
            })
    return {
        "coin_type": coin_type,
        "items": items,
        "total": len(items) if items else None,
        "needs_key": False,
    }


async def tron_token(a):
    h = {}
    k = os.getenv("TRONGRID_API_KEY", "").strip()
    if k:
        h["TRON-PRO-API-KEY"] = k
    async with aiohttp.ClientSession() as s:
        d = await http_json(s, "GET", f"https://api.trongrid.io/v1/contracts/{a}", headers=h)
    x = (d.get("data") or [{}])[0] if d and isinstance(d, dict) else {}
    return {"family": "tron", "chain": "TRON", "contract": a,
            "name": x.get("name") or "TRC-20 Contract",
            "symbol": x.get("symbol") or "???",
            "note": "TRON metadata is read from TronGrid."}


async def ton_token(a):
    h = {}
    k = os.getenv("TONCENTER_API_KEY", "").strip()
    if k:
        h["X-API-Key"] = k
    async with aiohttp.ClientSession() as s:
        d = await http_json(s, "GET", "https://toncenter.com/api/v3/jetton/masters",
                            params={"jetton_address": a, "limit": 1}, headers=h)
    x = (d.get("jetton_masters") or [{}])[0] if d and isinstance(d, dict) else {}
    cc = x.get("jetton_content") or {}
    return {"family": "ton", "chain": "TON", "contract": a,
            "name": cc.get("name") or x.get("name") or "Jetton",
            "symbol": cc.get("symbol") or x.get("symbol") or "???",
            "decimals": x.get("decimals"),
            "total_supply": x.get("total_supply"),
            "note": "TON Jetton metadata is read from TON Center."}


async def analyze_address(a):
    a = a.strip()
    f = detect_address_family(a)
    if f == "evm":
        m = await detect_evm(a)
        if not m:
            raise RuntimeError("No supported EVM deployment was detected.")
        return {"family": "evm", "matches": [await evm_token(a, c) for c in m]}
    if f == "solana":
        return await solana_token(a)
    if f == "sui":
        return await sui_token(a)
    if f == "tron":
        return await tron_token(a)
    if f == "ton":
        return await ton_token(a)
    raise RuntimeError("Address format not recognized.")


async def market_data(slug, a):
    try:
        async with aiohttp.ClientSession() as s:
            return await http_json(s, "GET", f"https://api.dexscreener.com/tokens/v1/{slug}/{a}") or []
    except:
        return []