import os, asyncio, re, time, aiohttp, json

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

EVM_RE=re.compile(r"^0x[a-fA-F0-9]{40}$")
SOL_RE=re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
SUI_RE=re.compile(r"^0x[a-fA-F0-9]{64}$")
TRON_RE=re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
TON_RE=re.compile(r"^(EQ|UQ)[A-Za-z0-9_-]{46}$")
SELECTORS={"name":"0x06fdde03","symbol":"0x95d89b41","decimals":"0x313ce567","totalSupply":"0x18160ddd"}


def short_address(a,l=10,r=8):
    return a if len(a)<=l+r+3 else f"{a[:l]}...{a[-r:]}"


def fmt_number(v):
    try:v=float(v)
    except:return str(v)
    for d,s in ((1e12,"T"),(1e9,"B"),(1e6,"M"),(1e3,"K")):
        if abs(v)>=d:return f"{v/d:.2f}{s}"
    return f"{v:.2f}"


def detect_address_family(a):
    if EVM_RE.fullmatch(a):return "evm"
    if TRON_RE.fullmatch(a):return "tron"
    if TON_RE.fullmatch(a):return "ton"
    if SUI_RE.fullmatch(a) or ("::" in a and a.startswith("0x")):return "sui"
    if SOL_RE.fullmatch(a):return "solana"
    return "unknown"


async def http_json(s,method,url,**kw):
    try:
        async with s.request(method,url,timeout=TIMEOUT,**kw) as r:
            text=await r.text()
            if r.status!=200:return {"__http_error__":r.status,"__text__":text[:1200]}
            try:return json.loads(text)
            except:return None
    except Exception:return None


async def rpc(s,url,method,params):
    d=await http_json(s,"POST",url,json={"jsonrpc":"2.0","id":1,"method":method,"params":params})
    if not d or d.get("error"):return None
    return d.get("result")


def alchemy_url(chain_id):
    key=os.getenv("ALCHEMY_API_KEY","").strip()
    c=EVM_CHAINS[chain_id]
    return c[2].format(key=key) if c[2] and key else None


async def detect_evm(a):
    key=os.getenv("ALCHEMY_API_KEY","").strip()
    async with aiohttp.ClientSession() as s:
        async def probe(cid,c):
            name,slug,alchemy,public=c
            urls=([alchemy.format(key=key)] if alchemy and key else[])+([public] if public else[])
            for u in urls:
                code=await rpc(s,u,"eth_getCode",[a,"latest"])
                if code and code!="0x":return {"chain_id":cid,"name":name,"slug":slug}
            return None
        out=await asyncio.gather(*(probe(cid,c) for cid,c in EVM_CHAINS.items()),return_exceptions=True)
    return [x for x in out if isinstance(x,dict)]


def dec_uint(x):
    try:return int(x,16)
    except:return 0


def dec_string(x):
    try:
        h=x[2:]
        if len(h)>=128:
            off=int(h[:64],16)*2
            if off+64<=len(h):
                n=int(h[off:off+64],16)
                return bytes.fromhex(h[off+64:off+64+n*2]).decode(errors="ignore").strip()
        return bytes.fromhex(h).decode(errors="ignore").strip("\x00").strip()
    except:return ""


async def evm_token(a,c):
    key=os.getenv("ALCHEMY_API_KEY","").strip();_,_,alchemy,public=EVM_CHAINS[c["chain_id"]]
    urls=([alchemy.format(key=key)] if alchemy and key else[])+([public] if public else[])
    last="RPC unavailable"
    for u in urls:
        try:
            async with aiohttp.ClientSession() as s:
                vals=await asyncio.gather(*(rpc(s,u,"eth_call",[{"to":a,"data":sel},"latest"]) for sel in SELECTORS.values()))
            name,sym,dec,sup=vals;d=dec_uint(dec);supply=dec_uint(sup)/(10**d if d<78 else 1)
            return {"family":"evm","chain":c["name"],"chain_id":c["chain_id"],"slug":c["slug"],"contract":a,"name":dec_string(name) or"Unknown Token","symbol":dec_string(sym) or"???","decimals":d,"total_supply":supply}
        except Exception as e:last=str(e)
    raise RuntimeError(last)


async def blockscout_request(chain_id,path,params=None):
    key=os.getenv("BLOCKSCOUT_API_KEY","").strip()
    if not key:return None
    url=f"https://api.blockscout.com/{chain_id}/api/v2{path}"
    p=dict(params or {});p["apikey"]=key
    async with aiohttp.ClientSession() as s:return await http_json(s,"GET",url,params=p)


def parse_next_cursor(d):
    if not isinstance(d,dict):return None
    np=d.get("next_page_params") or d.get("nextPageParams")
    return np if isinstance(np,dict) and np else None


def normalize_blockscout_holder(x):
    if not isinstance(x,dict):return None
    addr=x.get("address_hash") or x.get("address") or x.get("holder_address_hash") or x.get("walletAddress")
    if isinstance(addr,dict):addr=addr.get("hash") or addr.get("address_hash")
    if not addr:return None
    raw=x.get("value") or x.get("balance") or x.get("token_balance") or x.get("amount") or "0"
    try:raw_int=int(raw)
    except:raw_int=0
    return {"address":addr,"raw":raw_int,"value":x.get("value_formatted") or x.get("balance_formatted") or str(raw_int),"percent":x.get("percentage") or x.get("percent")}


async def blockscout_holders(a,c,cursor=None,limit=50):
    params=dict(cursor or {})
    params.setdefault("items_count", limit)
    d=await blockscout_request(c["chain_id"],f"/tokens/{a}/holders",params)
    if not isinstance(d,dict) or d.get("__http_error__"):return {"error":d}
    rows=d.get("items") or d.get("holders") or d.get("data") or d.get("result") or []
    items=[]
    for x in rows:
        h=normalize_blockscout_holder(x)
        if h:items.append(h)
    return {"items":items[:limit],"next":parse_next_cursor(d)}


async def blockscout_holder_count(a,c):
    # Blockscout's counters response is not consistent across hosted instances.
    # Prefer an explicit holder count when the endpoint supplies one, otherwise
    # evm_holders() derives the exact count by walking the paginated holder index.
    d=await blockscout_request(c["chain_id"],f"/tokens/{a}/counters")
    if not isinstance(d,dict) or d.get("__http_error__"):return None
    candidates=[d.get("token_holders"),d.get("holders"),d.get("holder_count"),d.get("holders_count"),d.get("count")]
    if isinstance(d.get("data"),dict):
        candidates += [d["data"].get("token_holders"),d["data"].get("holders"),d["data"].get("holder_count"),d["data"].get("count")]
    for x in candidates:
        try:
            if x is not None:return int(x)
        except:pass
    return None


async def cmc_keyless_holders(a,platform):
    url="https://pro-api.coinmarketcap.com/public-api/v1/dex/holders/list"
    body={"tokenAddress":a,"platform":platform,"tag":"tag_all"}
    async with aiohttp.ClientSession() as s:d=await http_json(s,"POST",url,json=body,headers={"Content-Type":"application/json"})
    if not isinstance(d,dict) or d.get("__http_error__"):return None
    rows=d.get("holders") or (d.get("data") or {}).get("holders") or d.get("data") or []
    items=[]
    for x in rows:
        if not isinstance(x,dict):continue
        addr=x.get("walletAddress") or x.get("address") or x.get("holderAddress")
        if addr:items.append({"address":addr,"value":x.get("balance") or x.get("actualBalance") or x.get("spotPosition") or "0","percent":x.get("percent")})
    return items


async def cmc_keyless_count(a,platform):
    url="https://pro-api.coinmarketcap.com/public-api/v1/dex/holders/count"
    async with aiohttp.ClientSession() as s:d=await http_json(s,"GET",url,params={"platform":platform,"tokenAddress":a})
    if not isinstance(d,dict) or d.get("__http_error__"):return None
    x=d.get("count") or (d.get("data") or {}).get("count")
    try:return int(x)
    except:return None


async def evm_holders(a,c):
    # Keep the approved Robinhood-style UX: the UI displays only 10 holders per
    # page, while the backend builds the complete indexed holder list so the
    # displayed total is the actual full count rather than the first page size.
    items=[];cursor=None
    for _ in range(200):
        page=await blockscout_holders(a,c,cursor,50)
        if page.get("error"):break
        rows=page.get("items") or []
        items.extend(rows)
        cursor=page.get("next")
        if not cursor or not rows:break
    if items:
        return {"provider":"blockscout","items":items,"total":len(items),"next":None,"source":"Blockscout","page_size":10,"has_next":False}
    cmc_items=await cmc_keyless_holders(a,c["slug"])
    if cmc_items:
        return {"provider":"cmc","items":cmc_items,"total":await cmc_keyless_count(a,c["slug"]),"next":None,"source":"CoinMarketCap keyless","page_size":10,"all_items":cmc_items,"has_next":False}
    raise RuntimeError("No indexed holder provider returned data for this EVM token.")



async def evm_holder_next(a,c,cursor):
    d=await blockscout_holders(a,c,cursor,10)
    if d.get("error"):raise RuntimeError("Blockscout holder page request failed.")
    return d


async def solana_rpc_call(s, url, method, params):
    """Solana RPC wrapper with explicit error handling and provider fallback.

    This is intentionally isolated from EVM RPCs.  Robinhood/EVM routing is
    not involved here.
    """
    d=await http_json(s,"POST",url,json={"jsonrpc":"2.0","id":1,"method":method,"params":params})
    if not isinstance(d,dict):
        return None
    if d.get("error"):
        return None
    return d.get("result")


def solana_rpc_urls():
    key=os.getenv("ALCHEMY_API_KEY","").strip()
    urls=[]
    if key:
        urls.append(f"https://solana-mainnet.g.alchemy.com/v2/{key}")
    # Public RPC fallbacks are used only for ordinary Solana RPC calls. DAS
    # holder indexing remains Alchemy-backed below.
    urls += [
        "https://api.mainnet-beta.solana.com",
        "https://solana-rpc.publicnode.com",
    ]
    return urls


async def solana_token(a):
    """Analyze an SPL mint without changing the EVM analysis path."""
    last="Solana RPC unavailable"
    for u in solana_rpc_urls():
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as s:
                # getTokenSupply is standard Solana JSON-RPC and is the only
                # required call for a valid SPL mint/supply result.
                supply=await solana_rpc_call(s,u,"getTokenSupply",[a])
                if not isinstance(supply,dict):
                    continue
                v=supply.get("value") or {}
                d=int(v.get("decimals",0) or 0)
                raw=int(v.get("amount","0") or 0)

                # Metadata is optional: Alchemy DAS gives richer metadata, but
                # failure to retrieve it must never turn a valid mint into an
                # "RPC unavailable" error.
                asset=None
                if u.startswith("https://solana-mainnet.g.alchemy.com/"):
                    asset=await solana_rpc_call(s,u,"getAsset",[a,{"displayOptions":{"showFungible":True}}])

                content=((asset or {}).get("content") or {})
                md=(content.get("metadata") or {})
                ti=(asset or {}).get("token_info") or {}
                name=md.get("name") or ti.get("name") or (asset or {}).get("name") or ""
                symbol=md.get("symbol") or ti.get("symbol") or (asset or {}).get("symbol") or ""
                if (not name or not symbol) and content.get("json_uri"):
                    try:
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as ms:
                            meta=await http_json(ms,"GET",content["json_uri"])
                        if isinstance(meta,dict):
                            name=name or meta.get("name") or ""
                            symbol=symbol or meta.get("symbol") or ""
                    except Exception:
                        pass
                return {
                    "family":"solana","chain":"Solana","contract":a,
                    "name":name or "SPL Token","symbol":symbol or "???",
                    "decimals":d,"total_supply":raw/(10**d if d else 1)
                }
        except Exception as e:
            last=str(e)
    raise RuntimeError(last if last else "Solana RPC unavailable")


async def solana_token_account_page(owner,mint):
    key=os.getenv("ALCHEMY_API_KEY","").strip()
    urls=solana_rpc_urls()
    for u in urls:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as s:
                d=await solana_rpc_call(s,u,"getTokenAccountsByOwner",[owner,{"mint":mint},{"encoding":"jsonParsed"}])
            if not isinstance(d,list):
                continue
            out=[]
            for x in d:
                info=((((x.get("account") or {}).get("data") or {}).get("parsed") or {}).get("info") or {})
                ta=info.get("tokenAmount") or {}
                try: raw=int(ta.get("amount") or 0)
                except: raw=0
                if raw<=0: continue
                out.append({"address":x.get("pubkey"),"raw":raw,"decimals":ta.get("decimals"),"value":ta.get("uiAmountString") or str(raw)})
            return out
        except Exception:
            continue
    return []


async def solana_all_holders(a):
    """Return unique wallet owners for a Solana mint.

    Primary source: Alchemy DAS getTokenAccounts.
    Fallback: standard Solana getProgramAccounts for both SPL Token and
    Token-2022 programs.  No Blockscout key is involved.
    """
    key=os.getenv("ALCHEMY_API_KEY","").strip()
    if not key:
        raise RuntimeError("ALCHEMY_API_KEY is required for full Solana holder indexing.")
    alchemy=f"https://solana-mainnet.g.alchemy.com/v2/{key}"
    owners={}; token_accounts=0

    def add_rows(rows):
        nonlocal token_accounts
        for x in rows or []:
            if not isinstance(x,dict): continue
            owner=x.get("owner"); amount=x.get("amount")
            acct=x.get("account") or {}
            data=acct.get("data") or {}
            parsed=data.get("parsed") or {}
            info=parsed.get("info") or {}
            owner=owner or info.get("owner") or acct.get("owner")
            if amount is None: amount=(info.get("tokenAmount") or {}).get("amount")
            if amount is None and isinstance(x.get("tokenAmount"),dict): amount=x["tokenAmount"].get("amount")
            try: raw=int(amount or 0)
            except: raw=0
            if owner and raw>0:
                owners[owner]=owners.get(owner,0)+raw
                token_accounts+=1

    async def scan_das(s):
        cursor=None
        saw=False
        for _ in range(10000):
            params={"mintAddress":a,"limit":1000,"options":{"showZeroBalance":False}}
            if cursor: params["cursor"]=cursor
            else: params["page"]=1
            d=await solana_rpc_call(s,alchemy,"getTokenAccounts",params)
            if not isinstance(d,dict): return saw
            rows=d.get("token_accounts") or d.get("tokenAccounts") or []
            if isinstance(rows,list) and rows:
                saw=True; add_rows(rows)
            cursor=d.get("cursor")
            if not cursor:
                return saw
        return saw

    async def scan_program(s,base,program):
        nonlocal token_accounts
        # First use the paginated Alchemy method.
        cursor=None; found=False
        for _ in range(10000):
            cfg={"encoding":"jsonParsed","limit":1000,"filters":[{"memcmp":{"offset":0,"bytes":a}}]}
            if cursor: cfg["paginationKey"]=cursor
            d=await solana_rpc_call(s,alchemy,"getProgramAccountsV2",[program,cfg])
            if not isinstance(d,dict): break
            rows=d.get("accounts")
            cursor=d.get("paginationKey")
            if rows is None and isinstance(d.get("value"),dict):
                v=d["value"]; rows=v.get("accounts") or v.get("value") or []; cursor=v.get("paginationKey")
            if not isinstance(rows,list) or not rows: break
            found=True
            add_rows(rows)
            if not cursor: break
        if found: return True

        # Final fallback to ordinary Solana RPC.  This is deliberately a
        # separate provider path so a DAS outage does not make /holders fail.
        public="https://api.mainnet-beta.solana.com"
        cfg={"encoding":"jsonParsed","filters":[{"memcmp":{"offset":0,"bytes":a}}]}
        d=await solana_rpc_call(s,public,"getProgramAccounts",[program,cfg])
        if isinstance(d,list) and d:
            add_rows(d); return True
        return False

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=35)) as s:
        try:
            das_ok=await scan_das(s)
        except Exception:
            das_ok=False
        if not das_ok or not owners:
            owners.clear(); token_accounts=0
            await scan_program(s,"SPL","TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
            await scan_program(s,"Token-2022","TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")

    items=[{"address":o,"raw":v,"value":str(v)} for o,v in owners.items() if v>0]
    items.sort(key=lambda x:x["raw"],reverse=True)
    if not items:
        raise RuntimeError("No non-zero Solana token accounts were found for this mint.")
    return {"items":items,"total":len(items),"source":"Solana token accounts (unique wallet owners)","token_accounts":token_accounts,"page_size":10}


async def evm_market_data(slug,a):
    """Return DexScreener pairs for an EVM token.

    IMPORTANT: this function is isolated from all holder logic.  The Robinhood
    holder architecture is not touched by market-data lookups.

    DexScreener can expose the same token through more than one route, so we
    try the chain-specific token-pairs endpoint first, then the token endpoint
    and finally the generic token/search endpoints.  Every returned pair is
    still filtered by BOTH chainId and the exact token contract address.
    """
    slug=str(slug or "").strip().lower()
    address=str(a or "").strip()
    if not slug or not EVM_RE.fullmatch(address):
        return []

    endpoints = [
        # Preferred route: returns all indexed pools for this token on a chain.
        f"https://api.dexscreener.com/token-pairs/v1/{slug}/{address}",
        # Existing public token route.
        f"https://api.dexscreener.com/tokens/v1/{slug}/{address}",
        # Generic route; filter by chain/address below.
        f"https://api.dexscreener.com/latest/dex/tokens/{address}",
    ]

    candidates=[]
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            for endpoint in endpoints:
                for attempt in range(3):
                    data=await http_json(session,"GET",endpoint)
                    if isinstance(data,list):
                        candidates.extend(data)
                        break
                    if isinstance(data,dict) and isinstance(data.get("pairs"),list):
                        candidates.extend(data["pairs"])
                        break
                    status=data.get("__http_error__") if isinstance(data,dict) else None
                    if status in (429,500,502,503,504) and attempt < 2:
                        await asyncio.sleep(0.75*(attempt+1))
                        continue
                    break

            # Last-resort address search.  This is intentionally after the
            # exact token endpoints so a search result can never bypass the
            # exact chain/address validation below.
            for attempt in range(3):
                data=await http_json(
                    session,
                    "GET",
                    "https://api.dexscreener.com/latest/dex/search",
                    params={"q":address},
                )
                if isinstance(data,dict) and isinstance(data.get("pairs"),list):
                    candidates.extend(data["pairs"])
                    break
                status=data.get("__http_error__") if isinstance(data,dict) else None
                if status in (429,500,502,503,504) and attempt < 2:
                    await asyncio.sleep(0.75*(attempt+1))
                    continue
                break
    except Exception:
        return []

    target=address.lower()
    wanted_chain=slug
    exact=[]
    seen=set()

    def num(v):
        try:return float(v or 0)
        except:return 0.0

    for pair in candidates:
        if not isinstance(pair,dict):
            continue
        chain_id=str(pair.get("chainId") or "").strip().lower()
        if chain_id != wanted_chain:
            continue
        base=pair.get("baseToken") or {}
        quote=pair.get("quoteToken") or {}
        base_address=str(base.get("address") or "").lower()
        quote_address=str(quote.get("address") or "").lower()
        if target not in (base_address,quote_address):
            continue

        pair_id=str(pair.get("pairAddress") or pair.get("url") or "")
        if pair_id in seen:
            continue
        seen.add(pair_id)
        exact.append(pair)

    # Highest-liquidity pool first.  Never let one malformed liquidity field
    # make the entire market-data lookup fail.
    exact.sort(key=lambda p:num((p.get("liquidity") or {}).get("usd")),reverse=True)
    return exact


SUI_RPC="https://fullnode.mainnet.sui.io:443"
async def sui_rpc(method,params):
    async with aiohttp.ClientSession() as s:return await rpc(s,SUI_RPC,method,params)

async def sui_resolve_coin_type(a):
    if "::" in a:return a
    obj=await sui_rpc("sui_getObject",[a,{"showType":True,"showContent":True,"showOwner":True}]);typ=((obj or {}).get("data") or {}).get("type") or ""
    m=re.search(r"(?:0x2::coin::Coin|0x2::coin::CoinMetadata)<(.+)>$",typ)
    if m:return m.group(1)
    raise RuntimeError("I could not derive a Sui coin type from that object. Send the full coin type.")

async def sui_token(a):
    coin_type=await sui_resolve_coin_type(a);md=await sui_rpc("suix_getCoinMetadata",[coin_type]);sup=await sui_rpc("suix_getTotalSupply",[coin_type])
    if md is None:raise RuntimeError("Sui RPC could not find coin metadata for that coin type.")
    d=int((md or {}).get("decimals",0));raw=int(((sup or {}).get("value",0) or 0))
    return {"family":"sui","chain":"Sui","contract":coin_type,"input":a,"name":md.get("name") or"Unknown Sui Coin","symbol":md.get("symbol") or"???","decimals":d,"total_supply":raw/(10**d if d else 1),"coin_type":coin_type}

async def sui_holders(a):
    coin_type=await sui_resolve_coin_type(a);key=os.getenv("BLOCKVISION_API_KEY","").strip()
    if not key:return {"coin_type":coin_type,"items":[],"total":None,"needs_key":True}
    cursor=None;items=[];total=None
    async with aiohttp.ClientSession() as s:
        for _ in range(2000):
            params={"coinType":coin_type,"limit":50}
            if cursor:params["cursor"]=cursor
            d=await http_json(s,"GET","https://api.blockvision.org/v2/sui/coin/holders",params=params,headers={"x-api-key":key})
            if not isinstance(d,dict) or d.get("__http_error__"):raise RuntimeError("BlockVision holder API request failed.")
            rows=d.get("data") or [];total=d.get("total",total)
            for x in rows:
                addr=x.get("address") or x.get("holderAddress") or x.get("owner")
                if addr:items.append({"address":addr,"value":x.get("quantity") or x.get("amount") or x.get("balance") or "0","percent":x.get("percentage")})
            cursor=d.get("nextPageCursor")
            if not cursor or not rows:break
    return {"coin_type":coin_type,"items":items,"total":total if total is not None else len(items),"source":"BlockVision","needs_key":False}


async def tron_token(a):
    async with aiohttp.ClientSession() as s:d=await http_json(s,"GET","https://api.trongrid.io/v1/trc20/info",params={"contract_list":a})
    x=(d.get("data") or [{}])[0] if isinstance(d,dict) else {}
    return {"family":"tron","chain":"TRON","contract":a,"name":x.get("name") or"TRC-20 Token","symbol":x.get("symbol") or"???","decimals":x.get("decimals"),"total_supply":x.get("total_supply"),"holder_count":x.get("holders") or x.get("holder_count")}

async def tron_holder_page(a,offset):
    async with aiohttp.ClientSession() as s:d=await http_json(s,"GET","https://apilist.tronscanapi.com/api/tokenholders",params={"address":a,"start":offset,"limit":10,"sort":"-balance"})
    if not isinstance(d,dict) or d.get("__http_error__"):raise RuntimeError("TronScan holder index did not accept the public request. No extra API key is configured.")
    rows=d.get("data") or [];total=d.get("rangeTotal") or d.get("total") or 0
    items=[{"address":x.get("address"),"value":x.get("balance") or x.get("quantity") or x.get("amount") or "0","percent":x.get("percent") or x.get("tokenRatio")} for x in rows if x.get("address")]
    return {"items":items,"total":total,"has_next":offset+len(items)<total}

async def tron_holders(a):
    return await tron_holder_page(a,0)


async def ton_token(a):
    async with aiohttp.ClientSession() as s:d=await http_json(s,"GET",f"https://tonapi.io/v2/jettons/{a}")
    if not isinstance(d,dict) or d.get("__http_error__"):raise RuntimeError("TONAPI could not find that Jetton.")
    md=d.get("metadata") or {}
    return {"family":"ton","chain":"TON","contract":a,"name":md.get("name") or d.get("name") or"Jetton","symbol":md.get("symbol") or d.get("symbol") or"???","decimals":d.get("decimals"),"total_supply":d.get("total_supply") or d.get("totalSupply")}

async def ton_all_holders(a):
    items=[];last=None
    async with aiohttp.ClientSession() as s:
        for _ in range(5000):
            params={"limit":50,"sort_by":"address"}
            if last:params["last_account_id"]=last
            d=await http_json(s,"GET",f"https://tonapi.io/v2/jettons/{a}/holders",params=params)
            if not isinstance(d,dict) or d.get("__http_error__"):raise RuntimeError("TONAPI holder lookup failed.")
            rows=d.get("addresses") or d.get("holders") or []
            for x in rows:
                addr=x.get("address") if isinstance(x,dict) else None
                if addr:items.append({"address":addr,"value":x.get("balance") or x.get("amount") or "0","percent":x.get("percentage")})
            if not rows or len(rows)<50:break
            last=rows[-1].get("address")
            if len(items)>=100000:raise RuntimeError("TON holder safety limit reached at 100,000 holders.")
    return {"items":items,"total":len(items),"source":"TONAPI","page_size":10}


async def analyze_address(a):
    a=a.strip();f=detect_address_family(a)
    if f=="evm":
        m=await detect_evm(a)
        if not m:raise RuntimeError("No supported EVM deployment was detected.")
        return {"family":"evm","matches":[await evm_token(a,c) for c in m]}
    if f=="solana":return await solana_token(a)
    if f=="sui":return await sui_token(a)
    if f=="tron":return await tron_token(a)
    if f=="ton":return await ton_token(a)
    raise RuntimeError("Address format not recognized.")


async def wallet_details(family,address,chain=None):
    if family=="evm":
        cid=chain["chain_id"];_,_,alchemy,public=EVM_CHAINS[cid];key=os.getenv("ALCHEMY_API_KEY","").strip();urls=([alchemy.format(key=key)] if alchemy and key else[])+([public] if public else[])
        async with aiohttp.ClientSession() as s:
            for u in urls:
                bal=await rpc(s,u,"eth_getBalance",[address,"latest"]);nonce=await rpc(s,u,"eth_getTransactionCount",[address,"latest"]);code=await rpc(s,u,"eth_getCode",[address,"latest"])
                if bal is not None:return {"type":"Contract" if code and code!="0x" else "Wallet/EOA","native":int(bal,16)/1e18,"tx_count":int(nonce,16),"chain":chain["name"]}
    if family=="solana":
        key=os.getenv("ALCHEMY_API_KEY","").strip();u=f"https://solana-mainnet.g.alchemy.com/v2/{key}" if key else"https://api.mainnet-beta.solana.com"
        async with aiohttp.ClientSession() as s:
            bal=await rpc(s,u,"getBalance",[address]);tx=await rpc(s,u,"getSignaturesForAddress",[address,{"limit":1}])
        return {"type":"Solana account","native":((bal or {}).get("value",0))/1e9,"recent_activity":len(tx or [])}
    if family=="sui":
        b=await sui_rpc("suix_getBalance",[address]);return {"type":"Sui address","native":int((b or {}).get("totalBalance",0))/1e9}
    if family=="ton":
        async with aiohttp.ClientSession() as s:d=await http_json(s,"GET",f"https://tonapi.io/v2/accounts/{address}")
        return {"type":"TON account","native":(d or {}).get("balance",0)/1e9}
    if family=="tron":
        async with aiohttp.ClientSession() as s:d=await http_json(s,"GET",f"https://api.trongrid.io/v1/accounts/{address}")
        x=(d.get("data") or [{}])[0] if isinstance(d,dict) else {};return {"type":"TRON account","native":x.get("balance",0)/1e6,"tx_count":x.get("transactions",0)}
    return {}


async def market_data(slug,a):
    try:
        async with aiohttp.ClientSession() as s:return await http_json(s,"GET",f"https://api.dexscreener.com/tokens/v1/{slug}/{a}") or []
    except:return []
