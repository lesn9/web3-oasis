import os, asyncio, uuid, html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from analysis import analyze_address,get_holders_page,blockscout_holder_count,market_data,fmt_number,short_address

SESSIONS={}

def arg(u):
    p=u.message.text.split(maxsplit=1)
    return p[1].strip() if len(p)>1 else ''

async def start(u,c):
    await u.message.reply_text('🤖 <b>Web3 Oasis</b>\n\nAutomatic chain detection is enabled.\n\n/analyze <code>address</code>\n/holders <code>address</code>\n/risk <code>address</code>\n/report <code>address</code>',parse_mode='HTML')

async def analyze_cmd(u,c):
    a=arg(u)
    if not a:return await u.message.reply_text('Usage: /analyze <contract/address>')
    m=await u.message.reply_text('🔎 Detecting chain and analyzing…')
    try:
        r=await asyncio.wait_for(analyze_address(a),40)
        if r.get('family')=='evm':
            for x in r['matches']:
                t=f"🤖 <b>Web3 Oasis — Token Analysis</b>\n\n🪙 <b>{html.escape(x['name'])}</b> ({html.escape(x['symbol'])})\n⛓️ Chain: <b>{html.escape(x['chain'])}</b>\n🆔 Chain ID: {x['chain_id']}\n📜 Contract: <code>{html.escape(a)}</code>\n🔢 Decimals: {x['decimals']}\n💰 Total Supply: {fmt_number(x['total_supply'])} {html.escape(x['symbol'])}\n"
                markets=await market_data(x['slug'],a)
                if markets:
                    p=markets[0]
                    t+=f"\n📊 <b>Market Data</b>\n• Pair: {html.escape(p.get('baseToken',{}).get('symbol','?'))}/{html.escape(p.get('quoteToken',{}).get('symbol','?'))}\n• DEX: {html.escape(p.get('dexId','?'))}\n• Price: ${p.get('priceUsd','?')}\n• Liquidity: ${(p.get('liquidity') or {}).get('usd') or 0}\n"
                else:t+='\n📊 <b>Market Data</b>\n• No indexed DexScreener pair found.\n'
                await u.message.reply_text(t,parse_mode='HTML')
            return await m.delete()
        t=f"🤖 <b>Web3 Oasis — Token Analysis</b>\n\n🪙 <b>{html.escape(str(r.get('name','Unknown')))}</b> ({html.escape(str(r.get('symbol','???')))})\n⛓️ Chain: <b>{html.escape(str(r.get('chain')))}</b>\n📜 Address: <code>{html.escape(a)}</code>\n"
        if r.get('decimals') is not None:t+=f"🔢 Decimals: {r['decimals']}\n"
        if r.get('total_supply') is not None:t+=f"💰 Total Supply: {fmt_number(r['total_supply'])}\n"
        if r.get('note'):t+=f"\nℹ️ {html.escape(r['note'])}"
        if r.get('top_accounts'):
            t+='\n\n🏆 <b>Top Token Accounts</b>\n'
            for i,x in enumerate(r['top_accounts'][:10],1):t+=f"{i}. <code>{html.escape(x.get('address',''))}</code> — {x.get('uiAmount')}\n"
        await m.edit_text(t,parse_mode='HTML')
    except Exception as e:
        await m.edit_text(f'❌ Analysis failed:\n<code>{html.escape(str(e)[:900])}</code>',parse_mode='HTML')

async def holders_cmd(u,c):
    a=arg(u)
    if not a:return await u.message.reply_text('Usage: /holders <EVM token contract>')
    m=await u.message.reply_text('🔎 Detecting chain and loading holders…')
    try:
        r=await asyncio.wait_for(analyze_address(a),35)
        if r.get('family')!='evm': return await m.edit_text('⚠️ Holder pagination is currently available for EVM tokens.')
        matches=r.get('matches',[])
        if len(matches)!=1:
            return await m.edit_text('⚠️ This address exists on multiple supported EVM chains. Please use a chain-specific address flow before requesting holders.')
        ch=matches[0]
        page=await asyncio.wait_for(get_holders_page(a,ch),20)
        if not page or not page.get('items'):
            return await m.edit_text('⚠️ No holder records were returned by Blockscout for this token/chain. This does not prove the token has zero holders; the explorer may not have indexed holder data.')
        sid=uuid.uuid4().hex[:10]
        SESSIONS[sid]={'address':a,'chain':ch,'pages':[page],'page':0,'chunk':0,'total':await blockscout_holder_count(a,ch['chain_id'])}
        await m.delete(); await render(u,sid)
    except Exception as e:
        await m.edit_text(f'❌ Holder lookup failed:\n<code>{html.escape(str(e)[:900])}</code>',parse_mode='HTML')

async def render(target,sid):
    s=SESSIONS.get(sid)
    if not s:return
    p=s['pages'][s['page']]; items=p.get('items',[]); start=s['chunk']*10; visible=items[start:start+10]
    total=s['total'] if s['total'] is not None else 'not provided by explorer'
    t=f"👥 <b>Web3 Oasis — Holder Intelligence</b>\n\n🪙 Token: <b>{html.escape(s['chain'].get('name',''))}</b>\n⛓️ {html.escape(s['chain']['name'])}\n📜 <code>{html.escape(s['address'])}</code>\n👥 Explorer Holder Count: <b>{total}</b>\n\n🏆 <b>Holders {start+1}–{start+len(visible)}</b>\n\n"
    kb=[]
    for pos,x in enumerate(visible,start):
        label=f"{pos+1}. {short_address(x['address'],8,6)}"
        pct=x.get('percentage')
        if pct is not None:
            try: label+=f' · {float(pct):.2f}%'
            except: pass
        kb.append([InlineKeyboardButton(label,callback_data=f'ha:{sid}:{pos}')])
    nav=[]
    if s['chunk']>0 or s['page']>0: nav.append(InlineKeyboardButton('⬅️ Previous',callback_data=f'hp:{sid}'))
    if start+10<len(items) or p.get('next_page_params'): nav.append(InlineKeyboardButton('Next ➡️',callback_data=f'hn:{sid}'))
    if nav: kb.append(nav)
    kb.append([InlineKeyboardButton('🔄 Refresh',callback_data=f'hr:{sid}')])
    mk=InlineKeyboardMarkup(kb)
    if isinstance(target,Update): await target.message.reply_text(t,parse_mode='HTML',reply_markup=mk)
    else: await target.edit_message_text(t,parse_mode='HTML',reply_markup=mk)

async def cb(u,c):
    q=u.callback_query; await q.answer(); parts=q.data.split(':'); action,sid=parts[0],parts[1]; s=SESSIONS.get(sid)
    if not s:return await q.edit_message_text('Session expired. Run /holders again.')
    p=s['pages'][s['page']]
    if action=='ha':
        i=int(parts[2])
        if i<len(p['items']):
            addr=p['items'][i]['address']
            await q.message.reply_text(f"📋 <b>Full holder address</b>\n\n<code>{html.escape(addr)}</code>\n\nTap and hold the address to copy it.",parse_mode='HTML')
    elif action=='hr':
        s['pages'][s['page']]=await get_holders_page(s['address'],s['chain'])
        s['chunk']=0
        await render(q,sid)
    elif action=='hn':
        if s['chunk']*10+10<len(p['items']):
            s['chunk']+=1
        elif p.get('next_page_params'):
            nxt=await get_holders_page(s['address'],s['chain'],p['next_page_params'])
            if not nxt or not nxt.get('items'): return await q.answer('No more indexed holders returned.',show_alert=True)
            s['pages'].append(nxt); s['page']+=1; s['chunk']=0
        else: return await q.answer('No more indexed holders returned.',show_alert=True)
        await render(q,sid)
    elif action=='hp':
        if s['chunk']>0:s['chunk']-=1
        elif s['page']>0:
            s['page']-=1; s['chunk']=max(0,(len(s['pages'][s['page']]['items'])-1)//10)
        await render(q,sid)

async def risk(u,c): await u.message.reply_text('🛡️ Risk scoring is not being faked with a placeholder score. Current build exposes token and holder intelligence.')
async def report(u,c): await analyze_cmd(u,c)

def main():
    token=os.getenv('TELEGRAM_BOT_TOKEN','').strip()
    if not token: raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured.')
    app=Application.builder().token(token).build()
    app.add_handler(CommandHandler('start',start)); app.add_handler(CommandHandler('analyze',analyze_cmd)); app.add_handler(CommandHandler('holders',holders_cmd)); app.add_handler(CommandHandler('risk',risk)); app.add_handler(CommandHandler('report',report)); app.add_handler(CallbackQueryHandler(cb,pattern=r'^(ha|hn|hp|hr):'))
    app.run_polling(drop_pending_updates=True)

if __name__=='__main__': main()
