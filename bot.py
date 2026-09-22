import asyncio, html, uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from analysis import (
    analyze_address, evm_holders, evm_holder_next, solana_all_holders,
    sui_holders, tron_holders, tron_holder_page, ton_all_holders,
    wallet_details, market_data, evm_market_data, fmt_number, short_address, solana_token_account_page, token_creator
)

SESSIONS = {}
PAGE_SIZE = 10
SESSION_TTL = 1800


def arg(u):
    p=(u.message.text or '').split(maxsplit=1)
    return p[1].strip() if len(p)>1 else ''


def cleanup_sessions():
    import time
    now=time.time()
    for sid,s in list(SESSIONS.items()):
        if now-s.get('created',now)>SESSION_TTL:SESSIONS.pop(sid,None)


async def start(u,c):
    await u.message.reply_text(
        '🤖 <b>Web3 Oasis</b>\n\n'
        'Automatic chain detection is enabled.\n\n'
        '/analyze <code>address</code>\n'
        '/holders <code>address</code>\n'
        '/risk <code>address</code>\n'
        '/report <code>address</code>',parse_mode='HTML')


async def analyze_cmd(u,c):
    a=arg(u)
    if not a:return await u.message.reply_text('Usage: /analyze <contract/address>')
    m=await u.message.reply_text('🔎 Detecting chain and analyzing…')
    try:
        r=await asyncio.wait_for(analyze_address(a),90)
        if r.get('family')=='evm':
            for x in r['matches']:
                t=(f"🤖 <b>Web3 Oasis — Token Analysis</b>\n\n🪙 <b>{html.escape(x['name'])}</b> ({html.escape(x['symbol'])})\n"
                   f"⛓️ Chain: <b>{html.escape(x['chain'])}</b>\n🆔 Chain ID: {x['chain_id']}\n📜 Contract: <code>{html.escape(a)}</code>\n"
                   f"🔢 Decimals: {x['decimals']}\n💰 Total Supply: {fmt_number(x['total_supply'])} {html.escape(x['symbol'])}\n")
                markets=await evm_market_data(x['slug'],a)
                if markets:
                    p=markets[0];liq=(p.get('liquidity') or {}).get('usd')
                    t+=(f"\n📊 <b>Market Data</b>\n• Pair: {html.escape((p.get('baseToken') or {}).get('symbol','?'))}/{html.escape((p.get('quoteToken') or {}).get('symbol','?'))}\n"
                        f"• DEX: {html.escape(p.get('dexId','?'))}\n• Price: ${p.get('priceUsd','?')}\n• Liquidity: ${liq if liq is not None else '?'}\n"
                        f"• 24h Volume: ${((p.get('volume') or {}).get('h24')) if (p.get('volume') or {}).get('h24') is not None else '?'}\n"
                        f"• 24h Change: {((p.get('priceChange') or {}).get('h24')) if (p.get('priceChange') or {}).get('h24') is not None else '?'}%\n"
                        f"🔗 {html.escape(p.get('url',''))}\n")
                else:t+='\n📊 <b>Market Data</b>\n• No indexed DexScreener pair found.\n'
                await u.message.reply_text(t,parse_mode='HTML',disable_web_page_preview=True)
            await m.delete();return
        t=(f"🤖 <b>Web3 Oasis — Token Analysis</b>\n\n🪙 <b>{html.escape(str(r.get('name','Unknown')))}</b> ({html.escape(str(r.get('symbol','???')))})\n"
           f"⛓️ Chain: <b>{html.escape(str(r.get('chain')))}</b>\n📜 Address: <code>{html.escape(a)}</code>\n")
        if r.get('coin_type'):t+=f"🪙 Coin Type: <code>{html.escape(r['coin_type'])}</code>\n"
        if r.get('decimals') is not None:t+=f"🔢 Decimals: {r['decimals']}\n"
        if r.get('total_supply') is not None:
            symbol=str(r.get('symbol') or '').strip()
            t+=f"💰 Total Supply: {fmt_number(r['total_supply'])}{(' ' + html.escape(symbol)) if symbol else ''}\n"
        # Non-EVM chains use the same market-data layer when DexScreener has a
        # market indexed for that chain. Missing market data never invalidates
        # the underlying token analysis.
        market_slug={'solana':'solana','tron':'tron','sui':'sui','ton':'ton'}.get(r.get('family'))
        if market_slug:
            markets=await market_data(market_slug,a)
            t+='\n📊 <b>Market Data</b>\n'
            if markets:
                p=markets[0]
                liq=(p.get('liquidity') or {}).get('usd')
                base=(p.get('baseToken') or {}).get('symbol','?')
                quote=(p.get('quoteToken') or {}).get('symbol','?')
                t+=(f"• Pair: {html.escape(str(base))}/{html.escape(str(quote))}\n"
                    f"• DEX: {html.escape(str(p.get('dexId','?')))}\n"
                    f"• Price: ${p.get('priceUsd','?')}\n"
                    f"• Liquidity: ${liq if liq is not None else '?'}\n"
                    f"• 24h Volume: ${((p.get('volume') or {}).get('h24')) if (p.get('volume') or {}).get('h24') is not None else '?'}\n"
                    f"• 24h Change: {((p.get('priceChange') or {}).get('h24')) if (p.get('priceChange') or {}).get('h24') is not None else '?'}%\n")
                if p.get('marketCap') is not None:t+=f"• Market Cap: ${p.get('marketCap')}\n"
                if p.get('fdv') is not None:t+=f"• FDV: ${p.get('fdv')}\n"
                if p.get('url'):t+=f"🔗 {html.escape(str(p['url']))}\n"
            else:
                t+='• No indexed DexScreener pair found.\n'
        await m.edit_text(t,parse_mode='HTML',disable_web_page_preview=True)
    except Exception as e:
        await m.edit_text(f'❌ Analysis failed:\n<code>{html.escape(str(e)[:1200])}</code>',parse_mode='HTML')


def holder_percent(s,x):
    supply=s.get("supply_raw")
    try:
        raw=int(x.get("raw",0) or 0)
        sup=float(supply or 0)
        if raw<=0 or sup<=0:return None
        return (raw/sup)*100.0
    except Exception:
        return None


def fmt_percent(v):
    try:
        x=float(v)
        if x>=1:return f"{x:.2f}%"
        if x>=0.01:return f"{x:.4f}%"
        if x>=0.0001:return f"{x:.6f}%"
        return f"{x:.8f}%"
    except Exception:return "?"


async def build_session(a,r):
    family=r.get('family')
    creator=None
    if family=='evm':
        matches=r.get('matches',[])
        if len(matches)!=1:raise RuntimeError('This token is detected on multiple supported EVM chains. I need one unambiguous chain for holder data.')
        ch=matches[0];data=await asyncio.wait_for(evm_holders(a,ch),75)
        creator=await token_creator(family,a,r)
        return {'family':'evm','address':a,'chain':ch,'symbol':ch.get('symbol') or r.get('symbol',''),'items':data['items'],'page':0,'total':data.get('total'),'source':data['source'],'cursor':data.get('next'),'cursor_history':[None], 'provider':data.get('provider'),'all_items':data.get('all_items'),'has_next':data.get('has_next',False),'supply_raw':r.get('total_supply_raw'),'creator':creator}
    if family=='solana':
        data=await asyncio.wait_for(solana_all_holders(a),150)
        creator=await token_creator(family,a,r)
        return {'family':'solana','address':a,'chain':{'name':'Solana'},'symbol':r.get('symbol',''),'items':data['items'],'page':0,'total':data['total'],'source':data['source'],'provider':'local','has_next':False,'supply_raw':r.get('total_supply_raw'),'creator':creator}
    if family=='sui':
        data=await asyncio.wait_for(sui_holders(a),75)
        if data.get('needs_key'):raise RuntimeError('Sui holder indexing needs the BLOCKVISION_API_KEY already configured in Railway.')
        creator=await token_creator(family,a,r)
        return {'family':'sui','address':a,'coin_type':data['coin_type'],'chain':{'name':'Sui'},'symbol':r.get('symbol',''),'items':data['items'],'page':0,'total':data['total'],'source':data['source'],'provider':'local','has_next':False,'supply_raw':r.get('total_supply_raw'),'creator':creator}
    if family=='tron':
        data=await asyncio.wait_for(tron_holders(a),45)
        creator=await token_creator(family,a,r)
        return {'family':'tron','address':a,'chain':{'name':'TRON'},'symbol':r.get('symbol',''),'items':data['items'],'page':0,'total':data['total'],'source':'TronScan','provider':'offset','offset':0,'has_next':data.get('has_next',False),'supply_raw':r.get('total_supply_raw'),'creator':creator}
    if family=='ton':
        data=await asyncio.wait_for(ton_all_holders(a),150)
        creator=await token_creator(family,a,r)
        return {'family':'ton','address':a,'chain':{'name':'TON'},'symbol':r.get('symbol',''),'items':data['items'],'page':0,'total':data['total'],'source':data['source'],'provider':'local','has_next':False,'supply_raw':r.get('total_supply_raw'),'creator':creator}
    raise RuntimeError('Holder intelligence is not available for this address type.')


def page_rows(s):
    start=s['page']*PAGE_SIZE;end=min(start+PAGE_SIZE,len(s['items']))
    return s['items'][start:end],start,end


def holder_title(s):
    if s['family']=='evm':return s.get('symbol') or 'Token'
    if s['family']=='solana':return s.get('symbol') or 'SPL Token'
    if s['family']=='sui':return s.get('symbol') or 'Sui Coin'
    if s['family']=='tron':return s.get('symbol') or 'TRC Token'
    return s.get('symbol') or 'Jetton'


def holder_text(s):
    rows,start,end=page_rows(s);total=s.get('total')
    t=("👥 <b>Web3 Oasis — Holder Intelligence</b>\n\n"
       f"🪙 <b>{html.escape(holder_title(s))}</b>\n⛓️ {html.escape(s['chain']['name'])}\n📜 <code>{html.escape(s['address'])}</code>\n")
    cr=s.get('creator') or {}
    if cr.get('address'):
        t+=f"👤 <b>{html.escape(str(cr.get('label') or 'Creator / Deployer'))}</b>: <code>{html.escape(str(cr['address']))}</code>\n"
    else:
        t+="👤 <b>Creator / Deployer</b>: Not indexed\n"
    t+=(f"👥 <b>Total Holders: {total if total is not None else 'not supplied'}</b>\n"
       f"📄 <b>Showing {start+1}–{end}</b>\n"
       f"ℹ️ Source: {html.escape(s['source'])}")
    return t,rows,start


async def render(target,sid):
    cleanup_sessions();s=SESSIONS.get(sid)
    if not s:return
    t,rows,start=holder_text(s);kb=[]
    for pos,x in enumerate(rows,start):
        pct=holder_percent(s,x)
        label=f"{short_address(x['address'],10,6)} — {fmt_percent(pct) if pct is not None else '?'}"
        kb.append([InlineKeyboardButton(label,callback_data=f"hd:{sid}:{pos}")])
    nav=[]
    if s['page']>0:nav.append(InlineKeyboardButton('⬅️ Previous',callback_data=f"hp:{sid}"))
    has_next=(s['page']+1)*PAGE_SIZE<len(s['items']) or (s.get('provider')=='offset' and s.get('has_next',False)) or (s.get('provider')=='cmc' and (s['page']+1)*PAGE_SIZE<len(s.get('all_items',[])))
    if has_next:nav.append(InlineKeyboardButton('Next ➡️',callback_data=f"hn:{sid}"))
    if nav:kb.append(nav)
    kb.append([InlineKeyboardButton('🔄 Refresh',callback_data=f"hr:{sid}")])
    markup=InlineKeyboardMarkup(kb)
    if isinstance(target,Update):await target.message.reply_text(t,parse_mode='HTML',reply_markup=markup,disable_web_page_preview=True)
    else:await target.edit_message_text(t,parse_mode='HTML',reply_markup=markup,disable_web_page_preview=True)


async def holders_cmd(u,c):
    a=arg(u)
    if not a:return await u.message.reply_text('Usage: /holders <token contract/address>')
    m=await u.message.reply_text('🔎 Detecting chain…')
    try:
        r=await asyncio.wait_for(analyze_address(a),90)
        await m.edit_text('⏳ Building the holder index…')
        s=await build_session(a,r);sid=uuid.uuid4().hex[:10];s['created']=__import__('time').time();SESSIONS[sid]=s
        await m.delete();await render(u,sid)
    except Exception as e:
        await m.edit_text(f'❌ Holder lookup failed:\n<code>{html.escape(str(e)[:1200])}</code>',parse_mode='HTML')


async def holder_next(s):
    if s['provider']=='cmc':
        if (s['page']+1)*PAGE_SIZE < len(s.get('all_items',[])):
            s['page']+=1;return True
        return False
    if s['provider']=='blockscout':
        if (s['page']+1)*PAGE_SIZE<len(s['items']):
            s['page']+=1;return True
        return False
    if s['provider']=='offset':
        off=s['offset']+PAGE_SIZE;data=await tron_holder_page(s['address'],off)
        if not data['items']:return False
        s['items'].extend(data['items']);s['offset']=off;s['total']=data.get('total',s.get('total'));s['has_next']=data.get('has_next',False);s['page']+=1;return True
    if (s['page']+1)*PAGE_SIZE<len(s['items']):s['page']+=1;return True
    return False


async def holder_previous(s):
    if s['page']<=0:return False
    s['page']-=1
    return True


async def refresh_session(s):
    a=s['address'];r=await asyncio.wait_for(analyze_address(a),90);new=await build_session(a,r)
    keep={'family':new['family'],'address':new['address'],'chain':new['chain'],'symbol':new.get('symbol',''),'items':new['items'],'page':0,'total':new.get('total'),'source':new['source'],'provider':new.get('provider')}
    for k in ('cursor','cursor_history','offset','has_next','coin_type','all_items','supply_raw','creator'):keep[k]=new.get(k)
    keep['created']=__import__('time').time();s.clear();s.update(keep)


async def cb(u,c):
    q=u.callback_query;await q.answer();parts=q.data.split(':');action,sid=parts[0],parts[1];s=SESSIONS.get(sid)
    if not s:return await q.edit_message_text('Session expired. Run /holders again.')
    if action=='hd':
        i=int(parts[2]);rows,_,_=page_rows(s)
        if i>=len(s['items']):return
        x=s['items'][i];addr=x['address']
        try:details=await asyncio.wait_for(wallet_details(s['family'],addr,s.get('chain')),30)
        except Exception as e:details={'error':str(e)}
        token_accounts=[]
        if s['family']=='solana':
            try: token_accounts=await asyncio.wait_for(solana_token_account_page(addr,s['address']),30)
            except Exception as e: details['token_accounts_error']=str(e)
        t=(f"📋 <b>Holder Details</b>\n\n📍 Wallet Address\n<code>{html.escape(addr)}</code>\n\n"
           f"💰 Token Balance: <code>{html.escape(str(x.get('value','0')))}</code>\n")
        cr=s.get('creator') or {}
        if cr.get('address'):
            t+=f"\n👤 <b>{html.escape(str(cr.get('label') or 'Creator / Deployer'))}</b>\n<code>{html.escape(str(cr['address']))}</code>\n"
        if s['family']=='solana':
            t+=f"\n🪙 <b>Token Accounts: {len(token_accounts)}</b>\n"
            for ta in token_accounts:
                t+=f"• <code>{html.escape(str(ta.get('address','')))}</code> — {html.escape(str(ta.get('value','0')))}\n"
            if not token_accounts and details.get('token_accounts_error'):
                t+=f"ℹ️ Token-account details unavailable: <code>{html.escape(str(details['token_accounts_error'])[:400])}</code>\n"
        pct=holder_percent(s,x)
        if pct is not None:t+=f"📊 Supply Share: <code>{fmt_percent(pct)}</code>\n"
        if details.get('type'):t+=f"🏷️ Account Type: <b>{html.escape(str(details['type']))}</b>\n"
        if details.get('chain'):t+=f"⛓️ Chain: {html.escape(str(details['chain']))}\n"
        if details.get('native') is not None:t+=f"⛽ Native Balance: <code>{details['native']:.8f}</code>\n"
        if details.get('tx_count') is not None:t+=f"🔢 Transaction Count: <code>{details['tx_count']}</code>\n"
        if details.get('recent_activity') is not None:t+=f"🕒 Recent Activity: <code>{details['recent_activity']}</code>\n"
        if details.get('error'):t+=f"\nℹ️ Wallet details unavailable: <code>{html.escape(str(details['error'])[:500])}</code>\n"
        kb=[[InlineKeyboardButton('🔎 Analyze holder',callback_data=f"wa:{sid}:{i}")],[InlineKeyboardButton('⬅️ Back to holders',callback_data=f"hb:{sid}")]]
        return await q.message.reply_text(t,parse_mode='HTML',reply_markup=InlineKeyboardMarkup(kb),disable_web_page_preview=True)
    if action=='wa':
        i=int(parts[2]);addr=s['items'][i]['address']
        try:
            d=await wallet_details(s['family'],addr,s.get('chain'))
            text=(f"🔎 <b>Holder Wallet Analysis</b>\n\n📍 <code>{html.escape(addr)}</code>\n🏷️ {html.escape(str(d.get('type','Account')))}\n")
            for label,key in [('⛽ Native Balance','native'),('🔢 Transaction Count','tx_count'),('🕒 Recent Activity','recent_activity')]:
                if d.get(key) is not None:text+=f"{label}: <code>{d[key]}</code>\n"
            if d.get('chain'):text+=f"⛓️ Chain: {html.escape(str(d['chain']))}\n"
            text+='\nUse /analyze with the holder address for the raw address probe where supported.'
            await q.message.reply_text(text,parse_mode='HTML')
        except Exception as e:await q.message.reply_text(f"❌ Holder analysis failed: <code>{html.escape(str(e)[:700])}</code>",parse_mode='HTML')
        return
    if action=='hb':return await render(q,sid)
    if action=='hn':
        await q.answer('Loading next page…')
        ok=await holder_next(s)
        if not ok:return await q.answer('No more holders.',show_alert=True)
    elif action=='hp':
        ok=await holder_previous(s)
        if not ok:return await q.answer('Already on the first page.',show_alert=True)
    elif action=='hr':
        await q.answer('Refreshing…');await refresh_session(s)
    await render(q,sid)


async def risk(u,c):
    await u.message.reply_text('🛡️ Risk scoring is not being faked with a placeholder score. Current build exposes token and holder intelligence.')

async def report(u,c):await analyze_cmd(u,c)


def main():
    token=__import__('os').getenv('TELEGRAM_BOT_TOKEN','').strip()
    if not token:raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured.')
    app=Application.builder().token(token).build()
    app.add_handler(CommandHandler('start',start));app.add_handler(CommandHandler('analyze',analyze_cmd));app.add_handler(CommandHandler('holders',holders_cmd));app.add_handler(CommandHandler('risk',risk));app.add_handler(CommandHandler('report',report))
    app.add_handler(CallbackQueryHandler(cb,pattern=r'^(hd|wa|hb|hn|hp|hr):'))
    app.run_polling(drop_pending_updates=True)

if __name__=='__main__':main()
