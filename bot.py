import os, asyncio, uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from analysis import analyze_address,get_holders_page,blockscout_holder_count,market_data,fmt_number,short_address
SESSIONS={}
def arg(u):
 p=u.message.text.split(maxsplit=1); return p[1].strip() if len(p)>1 else ''
async def start(u,c):await u.message.reply_text('🤖 <b>Web3 Oasis</b>\n\nAutomatic chain detection is enabled.\n\n/analyze <code>address</code>\n/holders <code>address</code>\n/risk <code>address</code>\n/report <code>address</code>',parse_mode='HTML')
async def analyze_cmd(u,c):
 a=arg(u)
 if not a:return await u.message.reply_text('Usage: /analyze <contract/address>')
 m=await u.message.reply_text('🔎 Detecting chain and analyzing…')
 try:
  r=await asyncio.wait_for(analyze_address(a),30)
  if r.get('family')=='evm':
   for x in r['matches']:
    t=f"🤖 <b>Web3 Oasis — Token Analysis</b>\n\n🪙 <b>{x['name']}</b> ({x['symbol']})\n⛓️ Chain: <b>{x['chain']}</b>\n🆔 Chain ID: {x['chain_id']}\n📜 Contract: <code>{a}</code>\n🔢 Decimals: {x['decimals']}\n💰 Total Supply: {fmt_number(x['total_supply'])} {x['symbol']}\n"
    markets=await market_data(x['slug'],a)
    if markets:
     p=markets[0]; t+=f"\n📊 <b>Market Data</b>\n• Pair: {p.get('baseToken',{}).get('symbol','?')}/{p.get('quoteToken',{}).get('symbol','?')}\n• DEX: {p.get('dexId','?')}\n• Price: ${p.get('priceUsd','?')}\n• Liquidity: ${(p.get('liquidity') or {}).get('usd') or 0}\n"
    else:t+='\n📊 <b>Market Data</b>\n• No indexed DexScreener pair found.\n'
    await u.message.reply_text(t,parse_mode='HTML')
   return await m.delete()
  t=f"🤖 <b>Web3 Oasis — Token Analysis</b>\n\n🪙 <b>{r.get('name')}</b> ({r.get('symbol','???')})\n⛓️ Chain: <b>{r.get('chain')}</b>\n📜 Address: <code>{a}</code>\n"
  if r.get('decimals') is not None:t+=f"🔢 Decimals: {r['decimals']}\n"
  if r.get('total_supply') is not None:t+=f"💰 Total Supply: {fmt_number(r['total_supply'])}\n"
  if r.get('note'):t+=f"\nℹ️ {r['note']}"
  if r.get('top_accounts'):
   t+='\n\n🏆 <b>Top Token Accounts</b>\n'
   for i,x in enumerate(r['top_accounts'][:10],1):t+=f"{i}. <code>{x.get('address')}</code> — {x.get('uiAmount')}\n"
  await m.edit_text(t,parse_mode='HTML')
 except Exception as e:await m.edit_text(f'❌ Analysis failed:\n<code>{str(e)[:900]}</code>',parse_mode='HTML')
async def holders_cmd(u,c):
 a=arg(u)
 if not a:return await u.message.reply_text('Usage: /holders <EVM token contract>')
 m=await u.message.reply_text('🔎 Detecting chain and loading holders…')
 try:
  r=await asyncio.wait_for(analyze_address(a),25)
  if r.get('family')!='evm' or len(r.get('matches',[]))!=1:return await m.edit_text('Holder pagination currently uses Blockscout for a uniquely detected EVM token.')
  ch=r['matches'][0]; page=await get_holders_page(a,ch); sid=uuid.uuid4().hex[:10]
  SESSIONS[sid]={'address':a,'chain':ch,'pages':[page],'page':0,'chunk':0,'total':await blockscout_holder_count(a,ch['chain_id'])}
  await m.delete(); await render(u,sid)
 except Exception as e:await m.edit_text(f'❌ Holder lookup failed:\n<code>{str(e)[:900]}</code>',parse_mode='HTML')
async def render(target,sid):
 s=SESSIONS.get(sid)
 if not s:return
 p=s['pages'][s['page']]; items=p.get('items',[]); start=s['chunk']*10; visible=items[start:start+10]; views=max(1,(len(items)+9)//10); total=s['total'] if s['total'] is not None else 'indexed count unavailable'
 t=f"👥 <b>Web3 Oasis — Holder Intelligence</b>\n\n⛓️ {s['chain']['name']}\n📜 <code>{s['address']}</code>\n👥 Indexed Holder Count: <b>{total}</b>\n\n🏆 <b>Page {s['page']+1} · View {s['chunk']+1}/{views}</b>\n\n"
 kb=[]
 for pos,x in enumerate(visible,start):
  label=f"{pos+1}. {short_address(x['address'],8,6)}"; pct=x.get('percentage')
  if pct is not None:label+=f' · {float(pct):.2f}%'
  kb.append([InlineKeyboardButton(label,callback_data=f'ha:{sid}:{pos}')])
 nav=[]
 if s['chunk']>0 or s['page']>0:nav.append(InlineKeyboardButton('⬅️ Prev',callback_data=f'hp:{sid}'))
 if start+10<len(items) or p.get('next_page_params'):nav.append(InlineKeyboardButton('Next ➡️',callback_data=f'hn:{sid}'))
 if nav:kb.append(nav)
 kb.append([InlineKeyboardButton('🔄 Refresh',callback_data=f'hr:{sid}')])
 mk=InlineKeyboardMarkup(kb)
 if isinstance(target,Update):await target.message.reply_text(t,parse_mode='HTML',reply_markup=mk)
 else:await target.edit_message_text(t,parse_mode='HTML',reply_markup=mk)
async def cb(u,c):
 q=u.callback_query;await q.answer(); a,sid,*rest=q.data.split(':'); s=SESSIONS.get(sid)
 if not s:return await q.edit_message_text('Session expired. Run /holders again.')
 p=s['pages'][s['page']]
 if a=='ha':
  i=int(rest[0]);
  if i<len(p['items']):await q.message.reply_text(f"📋 <b>Full holder address</b>\n<code>{p['items'][i]['address']}</code>",parse_mode='HTML')
 elif a=='hr':
  s['pages'][s['page']]=await get_holders_page(s['address'],s['chain']);await render(q,sid)
 elif a=='hn':
  if s['chunk']*10+10<len(p['items']):s['chunk']+=1
  elif p.get('next_page_params'):
   s['pages'].append(await get_holders_page(s['address'],s['chain'],p['next_page_params']));s['page']+=1;s['chunk']=0
  await render(q,sid)
 elif a=='hp':
  if s['chunk']>0:s['chunk']-=1
  elif s['page']>0:s['page']-=1;s['chunk']=max(0,(len(s['pages'][s['page']]['items'])-1)//10)
  await render(q,sid)
async def risk(u,c):await u.message.reply_text('🛡️ Risk scoring is not being faked with a placeholder score. Current build exposes token and holder intelligence.')
async def report(u,c):await analyze_cmd(u,c)
def main():
 token=os.getenv('TELEGRAM_BOT_TOKEN','').strip()
 if not token:raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured.')
 app=Application.builder().token(token).build();app.add_handler(CommandHandler('start',start));app.add_handler(CommandHandler('analyze',analyze_cmd));app.add_handler(CommandHandler('holders',holders_cmd));app.add_handler(CommandHandler('risk',risk));app.add_handler(CommandHandler('report',report));app.add_handler(CallbackQueryHandler(cb,pattern=r'^(ha|hn|hp|hr):'));app.run_polling(drop_pending_updates=True)
if __name__=='__main__':main()
