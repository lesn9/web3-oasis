import os, asyncio, re, aiohttp

TIMEOUT=aiohttp.ClientTimeout(total=8)
EVM_CHAINS={
1:("Ethereum","ethereum","https://eth-mainnet.g.alchemy.com/v2/{key}","https://eth.llamarpc.com"),
8453:("Base","base","https://base-mainnet.g.alchemy.com/v2/{key}","https://base.llamarpc.com"),
42161:("Arbitrum One","arbitrum","https://arb-mainnet.g.alchemy.com/v2/{key}","https://arbitrum.llamarpc.com"),
10:("Optimism","optimism","https://opt-mainnet.g.alchemy.com/v2/{key}","https://optimism.llamarpc.com"),
137:("Polygon","polygon","https://polygon-mainnet.g.alchemy.com/v2/{key}","https://polygon.llamarpc.com"),
56:("BNB Smart Chain","bsc",None,"https://bsc-dataseed.binance.org"),
43114:("Avalanche C-Chain","avalanche","https://avax-mainnet.g.alchemy.com/v2/{key}","https://api.avax.network/ext/bc/C/rpc"),
59144:("Linea","linea",None,"https://rpc.linea.build"),324:("zkSync Era","zksync",None,"https://mainnet.era.zksync.io"),534352:("Scroll","scroll",None,"https://rpc.scroll.io"),5000:("Mantle","mantle",None,"https://rpc.mantle.xyz"),81457:("Blast","blast",None,"https://rpc.blast.io"),100:("Gnosis","gnosis",None,"https://rpc.gnosischain.com"),42220:("Celo","celo",None,"https://forno.celo.org"),130:("Unichain","unichain",None,"https://mainnet.unichain.org"),480:("World Chain","worldchain",None,"https://worldchain-mainnet.g.alchemy.com"),1868:("Soneium","soneium",None,"https://rpc.soneium.org"),11011:("Shape","shape",None,"https://mainnet.shape.network"),146:("Sonic","sonic",None,"https://rpc.soniclabs.com"),80094:("Berachain","berachain",None,"https://rpc.berachain.com"),143:("Monad","monad",None,"https://rpc.monad.xyz"),1329:("Sei","sei",None,"https://evm-rpc.sei-apis.com"),7777777:("Zora","zora",None,"https://rpc.zora.energy"),204:("opBNB","opbnb",None,"https://opbnb-mainnet-rpc.bnbchain.org"),1088:("Metis","metis",None,"https://andromeda.metis.io/?owner=1088"),33139:("ApeChain","apechain",None,"https://rpc.apechain.com/http"),34443:("Mode","mode",None,"https://mainnet.mode.network"),1284:("Moonbeam","moonbeam",None,"https://rpc.api.moonbeam.network"),4663:("Robinhood Chain","robinhood",None,"https://rpc.mainnet.chain.robinhood.com"),57073:("Ink","ink",None,"https://rpc-gel.inkonchain.com"),2741:("Abstract","abstract",None,"https://api.mainnet.abs.xyz"),1244:("Arc","arc",None,"https://rpc.arc.network")}
EVM_RE=re.compile(r'^0x[a-fA-F0-9]{40}$'); SOL_RE=re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'); SUI_RE=re.compile(r'^0x[a-fA-F0-9]{64}$'); TRON_RE=re.compile(r'^T[1-9A-HJ-NP-Za-km-z]{33}$'); TON_RE=re.compile(r'^(EQ|UQ)[A-Za-z0-9_-]{46}$')
SELECTORS={'name':'0x06fdde03','symbol':'0x95d89b41','decimals':'0x313ce567','totalSupply':'0x18160ddd'}

def short_address(a,l=10,r=8): return a if len(a)<=l+r+3 else f'{a[:l]}...{a[-r:]}'
def fmt_number(v):
 v=float(v)
 for d,s in ((1e9,'B'),(1e6,'M'),(1e3,'K')):
  if abs(v)>=d:return f'{v/d:.2f}{s}'
 return f'{v:.2f}'
def detect_address_family(a):
 if EVM_RE.fullmatch(a):return 'evm'
 if TRON_RE.fullmatch(a):return 'tron'
 if TON_RE.fullmatch(a):return 'ton'
 if SUI_RE.fullmatch(a) or ('::' in a and a.startswith('0x')):return 'sui'
 if SOL_RE.fullmatch(a):return 'solana'
 return 'unknown'
async def http_json(s,method,url,**kw):
 async with s.request(method,url,timeout=TIMEOUT,**kw) as r:
  t=await r.text()
  if r.status>=400: raise RuntimeError(f'HTTP {r.status}: {t[:250]}')
  return await r.json(content_type=None)
async def rpc(s,url,method,params):
 d=await http_json(s,'POST',url,json={'jsonrpc':'2.0','id':1,'method':method,'params':params})
 if d.get('error'):raise RuntimeError(str(d['error']))
 return d.get('result')
async def detect_evm(a):
 key=os.getenv('ALCHEMY_API_KEY','').strip()
 async with aiohttp.ClientSession() as s:
  async def probe(cid,c):
   name,slug,alchemy,public=c; urls=([alchemy.format(key=key)] if alchemy and key else [])+([public] if public else [])
   for u in urls:
    try:
     if (await rpc(s,u,'eth_getCode',[a,'latest']))!='0x':return {'chain_id':cid,'name':name,'slug':slug}
    except: pass
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
   off=int(h[:64],16)*2; n=int(h[off:off+64],16); return bytes.fromhex(h[off+64:off+64+n*2]).decode(errors='ignore').strip()
  return bytes.fromhex(h).decode(errors='ignore').strip('\x00').strip()
 except:return ''
async def evm_token(a,c):
 key=os.getenv('ALCHEMY_API_KEY','').strip(); _,_,alchemy,public=EVM_CHAINS[c['chain_id']]; urls=([alchemy.format(key=key)] if alchemy and key else [])+([public] if public else []); last=None
 for u in urls:
  try:
   async with aiohttp.ClientSession() as s:
    vals=await asyncio.gather(*(rpc(s,u,'eth_call',[{'to':a,'data':sel},'latest']) for sel in SELECTORS.values()))
   name,sym,dec,sup=vals; d=dec_uint(dec); supply=dec_uint(sup)/(10**d if d<78 else 1)
   return {'family':'evm','chain':c['name'],'chain_id':c['chain_id'],'slug':c['slug'],'contract':a,'name':dec_string(name) or 'Unknown Token','symbol':dec_string(sym) or '???','decimals':d,'total_supply':supply}
  except Exception as e:last=e
 raise RuntimeError(str(last))
async def blockscout_holders(a,cid,page_params=None):
 key=os.getenv('BLOCKSCOUT_API_KEY','').strip()
 if not key:raise RuntimeError('BLOCKSCOUT_API_KEY is not configured.')
 p={'apikey':key,'items_count':50}; p.update(page_params or {})
 async with aiohttp.ClientSession() as s:d=await http_json(s,'GET',f'https://api.blockscout.com/{cid}/api/v2/tokens/{a}/holders',params=p)
 items=[]
 for x in d.get('items',[]):
  h=x.get('address') or {}; items.append({'address':h.get('hash') or h.get('address_hash') or '','value':x.get('value') or x.get('token_value') or '0','percentage':x.get('percentage')})
 return {'items':items,'next_page_params':d.get('next_page_params')}
async def blockscout_holder_count(a,cid):
 key=os.getenv('BLOCKSCOUT_API_KEY','').strip()
 if not key:return None
 try:
  async with aiohttp.ClientSession() as s:d=await http_json(s,'GET',f'https://api.blockscout.com/{cid}/api/v2/tokens/{a}/counters',params={'apikey':key})
  for k in ('holders','token_holders','holders_count'):
   if k in d:return int(d[k])
 except:pass
 return None
async def get_holders_page(a,c,page_params=None):return await blockscout_holders(a,c['chain_id'],page_params)
async def solana_token(a):
 key=os.getenv('ALCHEMY_API_KEY','').strip()
 if not key:raise RuntimeError('ALCHEMY_API_KEY is required for Solana.')
 u=f'https://solana-mainnet.g.alchemy.com/v2/{key}'
 async with aiohttp.ClientSession() as s:supply,largest=await asyncio.gather(rpc(s,u,'getTokenSupply',[a]),rpc(s,u,'getTokenLargestAccounts',[a]))
 v=(supply or {}).get('value',{}); d=int(v.get('decimals',0)); raw=int(v.get('amount','0'))
 return {'family':'solana','chain':'Solana','contract':a,'name':'SPL Token','symbol':'','decimals':d,'total_supply':raw/(10**d if d else 1),'top_accounts':(largest or {}).get('value',[]),'note':'Top token accounts are shown; this is not a global holder count.'}
async def sui_token(a):
 if '::' not in a:return {'family':'sui','chain':'Sui','contract':a,'name':'Sui Object','symbol':'','note':'For token metadata, send the coin type, e.g. 0x...::module::TOKEN.'}
 async with aiohttp.ClientSession() as s:md,sup=await asyncio.gather(rpc(s,'https://fullnode.mainnet.sui.io:443','suix_getCoinMetadata',[a]),rpc(s,'https://fullnode.mainnet.sui.io:443','suix_getTotalSupply',[a]))
 md=md or {}; d=int(md.get('decimals',0)); raw=int((sup or {}).get('value','0'))
 return {'family':'sui','chain':'Sui','contract':a,'name':md.get('name') or 'Unknown Sui Coin','symbol':md.get('symbol') or '???','decimals':d,'total_supply':raw/(10**d if d else 1),'note':'Sui holder indexing is not presented as an exact global count here.'}
async def tron_token(a):
 h={}; k=os.getenv('TRONGRID_API_KEY','').strip()
 if k:h['TRON-PRO-API-KEY']=k
 async with aiohttp.ClientSession() as s:d=await http_json(s,'GET',f'https://api.trongrid.io/v1/contracts/{a}',headers=h)
 x=(d.get('data') or [{}])[0]; return {'family':'tron','chain':'TRON','contract':a,'name':x.get('name') or 'TRC-20 Contract','symbol':x.get('symbol') or '???','note':'TRON metadata is read from TronGrid.'}
async def ton_token(a):
 h={}; k=os.getenv('TONCENTER_API_KEY','').strip()
 if k:h['X-API-Key']=k
 async with aiohttp.ClientSession() as s:d=await http_json(s,'GET','https://toncenter.com/api/v3/jetton/masters',params={'jetton_address':a,'limit':1},headers=h)
 x=(d.get('jetton_masters') or [{}])[0]; c=x.get('jetton_content') or {}; return {'family':'ton','chain':'TON','contract':a,'name':c.get('name') or x.get('name') or 'Jetton','symbol':c.get('symbol') or x.get('symbol') or '???','decimals':x.get('decimals'),'total_supply':x.get('total_supply'),'note':'TON Jetton metadata is read from TON Center.'}
async def analyze_address(a):
 a=a.strip(); f=detect_address_family(a)
 if f=='evm':
  m=await detect_evm(a)
  if not m:raise RuntimeError('No supported EVM deployment was detected.')
  return {'family':'evm','matches':[await evm_token(a,c) for c in m]}
 if f=='solana':return await solana_token(a)
 if f=='sui':return await sui_token(a)
 if f=='tron':return await tron_token(a)
 if f=='ton':return await ton_token(a)
 raise RuntimeError('Address format not recognized.')
async def market_data(slug,a):
 try:
  async with aiohttp.ClientSession() as s:return await http_json(s,'GET',f'https://api.dexscreener.com/tokens/v1/{slug}/{a}')
 except:return []
