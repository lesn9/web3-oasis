import os
import asyncio
import uuid
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from analysis import (
    analyze_address, compute_evm_holders, sui_holders, market_data,
    fmt_number, short_address
)

SESSIONS = {}


def arg(u):
    p = u.message.text.split(maxsplit=1)
    return p[1].strip() if len(p) > 1 else ''


async def start(u, c):
    await u.message.reply_text(
        '🤖 <b>Web3 Oasis</b>\n\n'
        'Automatic chain detection is enabled.\n\n'
        '/analyze <code>address</code>\n'
        '/holders <code>address</code>\n'
        '/risk <code>address</code>\n'
        '/report <code>address</code>\n'
        '/help',
        parse_mode='HTML'
    )


async def help_cmd(u, c):
    await u.message.reply_text(
        '🤖 <b>Web3 Oasis — Commands</b>\n\n'
        '<b>/analyze &lt;address&gt;</b>\n'
        'Detect chain + token metadata + market data\n\n'
        '<b>/holders &lt;address&gt;</b>\n'
        'Holder intelligence with pagination\n\n'
        '<b>/risk &lt;address&gt;</b>\n'
        'Risk indicators (where data is available)\n\n'
        '<b>/report &lt;address&gt;</b>\n'
        'Full analysis (same as /analyze for now)\n\n'
        'Supported: many EVM chains, Solana, Sui, Tron, TON.\n'
        'Just paste the address — the bot detects the chain.',
        parse_mode='HTML'
    )


async def analyze_cmd(u, c):
    a = arg(u)
    if not a:
        return await u.message.reply_text('Usage: /analyze <contract/address>')
    m = await u.message.reply_text('🔎 Detecting chain and analyzing…')
    try:
        r = await asyncio.wait_for(analyze_address(a), 75)
        if r.get('family') == 'evm':
            for x in r['matches']:
                t = (
                    f"🤖 <b>Web3 Oasis — Token Analysis</b>\n\n"
                    f"🪙 <b>{html.escape(x['name'])}</b> ({html.escape(x['symbol'])})\n"
                    f"⛓️ Chain: <b>{html.escape(x['chain'])}</b>\n"
                    f"🆔 Chain ID: {x['chain_id']}\n"
                    f"📜 Contract: <code>{html.escape(a)}</code>\n"
                    f"🔢 Decimals: {x['decimals']}\n"
                    f"💰 Total Supply: {fmt_number(x['total_supply'])} {html.escape(x['symbol'])}\n"
                )
                markets = await market_data(x['slug'], a)
                if markets:
                    # Show the highest-liquidity pair first
                    markets = sorted(
                        markets,
                        key=lambda p: float((p.get('liquidity') or {}).get('usd') or 0),
                        reverse=True
                    )
                    p = markets[0]
                    liq = (p.get('liquidity') or {}).get('usd')
                    vol = (p.get('volume') or {}).get('h24')
                    chg = (p.get('priceChange') or {}).get('h24')
                    t += (
                        f"\n📊 <b>Market Data</b>\n"
                        f"• Pair: {html.escape((p.get('baseToken') or {}).get('symbol','?'))}/"
                        f"{html.escape((p.get('quoteToken') or {}).get('symbol','?'))}\n"
                        f"• DEX: {html.escape(p.get('dexId','?'))}\n"
                        f"• Price: ${p.get('priceUsd','?')}\n"
                        f"• Liquidity: ${fmt_number(liq) if liq is not None else '?'}\n"
                        f"• 24h Volume: ${fmt_number(vol) if vol is not None else '?'}\n"
                        f"• 24h Change: {chg if chg is not None else '?'}%\n"
                        f"🔗 {html.escape(p.get('url',''))}\n"
                    )
                    if len(markets) > 1:
                        t += f"\nℹ️ {len(markets)} pairs found — showing highest liquidity.\n"
                else:
                    t += '\n📊 <b>Market Data</b>\n• No indexed DexScreener pair found.\n'
                await u.message.reply_text(t, parse_mode='HTML', disable_web_page_preview=True)
            await m.delete()
            return

        # Non-EVM path
        t = (
            f"🤖 <b>Web3 Oasis — Token Analysis</b>\n\n"
            f"🪙 <b>{html.escape(str(r.get('name','Unknown')))}</b> ({html.escape(str(r.get('symbol','???')))})\n"
            f"⛓️ Chain: <b>{html.escape(str(r.get('chain')))}</b>\n"
            f"📜 Address: <code>{html.escape(a)}</code>\n"
        )
        if r.get('coin_type'):
            t += f"🪙 Coin Type: <code>{html.escape(r['coin_type'])}</code>\n"
        if r.get('decimals') is not None:
            t += f"🔢 Decimals: {r['decimals']}\n"
        if r.get('total_supply') is not None:
            t += f"💰 Total Supply: {fmt_number(r['total_supply'])}\n"
        if r.get('note'):
            t += f"\nℹ️ {html.escape(r['note'])}"
        if r.get('top_accounts'):
            t += '\n\n🏆 <b>Top Token Accounts</b>\n'
            for i, x in enumerate(r['top_accounts'][:10], 1):
                addr = x.get('address', '')
                amount = x.get('uiAmount') or x.get('uiAmountString') or x.get('amount', '?')
                t += f"{i}. <code>{html.escape(addr)}</code> — {amount}\n"
            t += "\nℹ️ These are token accounts, not necessarily unique wallet holders."
        await m.edit_text(t, parse_mode='HTML', disable_web_page_preview=True)
    except Exception as e:
        await m.edit_text(
            f'❌ Analysis failed:\n<code>{html.escape(str(e)[:1200])}</code>',
            parse_mode='HTML'
        )


async def holders_cmd(u, c):
    a = arg(u)
    if not a:
        return await u.message.reply_text('Usage: /holders <token contract/address>')
    m = await u.message.reply_text('🔎 Detecting chain…')
    try:
        r = await asyncio.wait_for(analyze_address(a), 75)

        if r.get('family') == 'evm':
            matches = r.get('matches', [])
            if len(matches) != 1:
                return await m.edit_text(
                    '⚠️ This address is detected on multiple supported EVM chains.\n'
                    'I need one unambiguous chain before building the holder list.\n\n'
                    'Try /analyze first to see the matches.'
                )
            ch = matches[0]
            await m.edit_text(
                f"⏳ Building the holder snapshot for <b>{html.escape(ch['name'])}</b>…\n\n"
                "This scans the token's indexed ERC-20 transfer history and calculates current non-zero balances.\n"
                "It may take longer for tokens with many transfers.",
                parse_mode='HTML'
            )
            data = await asyncio.wait_for(compute_evm_holders(a, ch), 150)
            if not data['items']:
                return await m.edit_text(
                    '⚠️ No non-zero holders were derived from the token transfer history.\n'
                    'That can mean the token has no indexed ERC-20 transfers or uses a non-standard transfer mechanism.'
                )
            sid = uuid.uuid4().hex[:10]
            SESSIONS[sid] = {
                'family': 'evm', 'address': a, 'chain': ch,
                'items': data['items'], 'page': 0,
                'total': data['total'], 'source': data['source'],
                'symbol': ch.get('symbol') or data['meta'].get('symbol', ''),
                'decimals': data['meta'].get('decimals', 18),
                'total_supply': data['meta'].get('total_supply'),
                'concentration': data.get('concentration')
            }
            await m.delete()
            await render(u, sid)
            return

        if r.get('family') == 'sui':
            await m.edit_text('⏳ Loading Sui holder index…')
            data = await asyncio.wait_for(sui_holders(a), 45)
            if data.get('needs_key'):
                return await m.edit_text(
                    'ℹ️ Sui token holders require an indexed Sui data provider.\n\n'
                    'The Sui RPC can resolve metadata and supply, but it does not expose a global “all holders” query.\n'
                    'Add a <code>BLOCKVISION_API_KEY</code> in Railway to enable the Sui holder list.\n\n'
                    f"Coin type: <code>{html.escape(data['coin_type'])}</code>",
                    parse_mode='HTML'
                )
            if not data.get('items'):
                return await m.edit_text('⚠️ The Sui holder index returned no holder records.')
            sid = uuid.uuid4().hex[:10]
            SESSIONS[sid] = {
                'family': 'sui', 'address': a, 'coin_type': data['coin_type'],
                'items': data['items'], 'page': 0, 'total': data.get('total'),
                'chain': {'name': 'Sui'}, 'source': 'BlockVision',
                'symbol': r.get('symbol', ''), 'total_supply': r.get('total_supply')
            }
            await m.delete()
            await render(u, sid)
            return

        if r.get('family') == 'solana':
            await m.edit_text(
                'ℹ️ Solana currently shows <b>Top Token Accounts</b> in /analyze.\n\n'
                'A full unique-holder list requires a dedicated Solana holder indexer.\n'
                'Token accounts ≠ unique wallet holders.',
                parse_mode='HTML'
            )
            return

        await m.edit_text(
            '⚠️ Global holder pagination is currently implemented for EVM tokens and Sui tokens (with BlockVision key).\n\n'
            'Solana shows top token accounts in /analyze.'
        )
    except Exception as e:
        await m.edit_text(
            f'❌ Holder lookup failed:\n<code>{html.escape(str(e)[:1200])}</code>',
            parse_mode='HTML'
        )


def holder_text(sid):
    s = SESSIONS.get(sid)
    if not s:
        return None
    page = s['page']
    start = page * 10
    end = min(start + 10, len(s['items']))
    visible = s['items'][start:end]
    total = s.get('total')

    if s['family'] == 'evm':
        title = f"🪙 {html.escape(s['symbol'] or 'Token')}"
        chain = html.escape(s['chain']['name'])
    else:
        title = f"🪙 {html.escape(s.get('symbol') or 'Sui Coin')}"
        chain = 'Sui'

    t = (
        "👥 <b>Web3 Oasis — Holder Intelligence</b>\n\n"
        f"{title}\n⛓️ {chain}\n"
        f"📜 <code>{html.escape(s['address'])}</code>\n"
    )
    if s.get('total_supply') is not None:
        t += f"💰 Total Supply: {fmt_number(s['total_supply'])}\n"
    t += (
        f"👥 <b>Calculated Holders: {total if total is not None else 'not supplied by indexer'}</b>\n"
        f"📄 <b>Showing {start+1}–{end}</b>\n"
        f"ℹ️ Source: {html.escape(s['source'])}\n"
    )

    # Concentration (EVM only for now)
    conc = s.get('concentration')
    if conc:
        t += (
            f"\n📊 <b>Distribution</b>\n"
            f"• Top 1: {conc.get('top1', '?')}%\n"
            f"• Top 5: {conc.get('top5', '?')}%\n"
            f"• Top 10: {conc.get('top10', '?')}%\n"
        )

    t += "\n🏆 <b>Top Holders</b>\n"
    for i, x in enumerate(visible, start + 1):
        addr = x['address']
        value = x.get('value', '0')
        t += f"<b>{i}.</b> <code>{html.escape(addr)}</code> — {fmt_number(value)}\n"
    return t, visible, start


async def render(target, sid):
    s = SESSIONS.get(sid)
    if not s:
        return
    rendered = holder_text(sid)
    if not rendered:
        return
    t, visible, start = rendered
    kb = []
    for pos, x in enumerate(visible, start):
        kb.append([InlineKeyboardButton(
            f"{pos}. {short_address(x['address'], 8, 6)}",
            callback_data=f"ha:{sid}:{pos}"
        )])
    nav = []
    if s['page'] > 0:
        nav.append(InlineKeyboardButton('⬅️ Previous', callback_data=f'hp:{sid}'))
    if (s['page'] + 1) * 10 < len(s['items']):
        nav.append(InlineKeyboardButton('Next ➡️', callback_data=f'hn:{sid}'))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton('🔄 Refresh', callback_data=f'hr:{sid}')])
    markup = InlineKeyboardMarkup(kb)
    if isinstance(target, Update):
        await target.message.reply_text(t, parse_mode='HTML', reply_markup=markup, disable_web_page_preview=True)
    else:
        await target.edit_message_text(t, parse_mode='HTML', reply_markup=markup, disable_web_page_preview=True)


async def cb(u, c):
    q = u.callback_query
    await q.answer()
    parts = q.data.split(':')
    action, sid = parts[0], parts[1]
    s = SESSIONS.get(sid)
    if not s:
        return await q.edit_message_text('Session expired. Run /holders again.')

    if action == 'ha':
        i = int(parts[2])
        if i < len(s['items']):
            addr = s['items'][i]['address']
            value = s['items'][i].get('value', '0')
            await q.message.reply_text(
                f"📋 <b>Full holder address</b>\n\n<code>{html.escape(addr)}</code>\n\n"
                f"Balance: <code>{html.escape(str(value))}</code>\n\n"
                "Tap and hold the address to copy it.",
                parse_mode='HTML'
            )
        return

    if action == 'hn':
        if (s['page'] + 1) * 10 < len(s['items']):
            s['page'] += 1
        else:
            return await q.answer('No more holders.', show_alert=True)
    elif action == 'hp':
        if s['page'] > 0:
            s['page'] -= 1
        else:
            return await q.answer('Already on the first page.', show_alert=True)
    elif action == 'hr':
        if s['family'] == 'evm':
            await q.answer('Refreshing holder snapshot…')
            data = await compute_evm_holders(s['address'], s['chain'])
            s['items'] = data['items']
            s['total'] = data['total']
            s['page'] = 0
            s['concentration'] = data.get('concentration')
        else:
            await q.answer('Refreshing…')
            data = await sui_holders(s['address'])
            s['items'] = data.get('items', [])
            s['total'] = data.get('total')
            s['page'] = 0
    await render(q, sid)


async def risk(u, c):
    a = arg(u)
    if not a:
        return await u.message.reply_text('Usage: /risk <address>')
    m = await u.message.reply_text('🛡️ Gathering risk indicators…')
    try:
        r = await asyncio.wait_for(analyze_address(a), 60)
        t = "🛡️ <b>Web3 Oasis — Risk Indicators</b>\n\n"
        t += f"📜 <code>{html.escape(a)}</code>\n"
        if r.get('family') == 'evm':
            matches = r.get('matches', [])
            if matches:
                x = matches[0]
                t += f"🪙 {html.escape(x['name'])} ({html.escape(x['symbol'])})\n"
                t += f"⛓️ {html.escape(x['chain'])}\n\n"
                t += "ℹ️ Current build focuses on token + holder intelligence.\n"
                t += "Full contract permission scanning (owner, mint, blacklist, etc.) is planned.\n\n"
                t += "Observed facts only — no fabricated risk scores."
        else:
            t += f"⛓️ {html.escape(str(r.get('chain')))}\n\n"
            t += "Risk scoring for non-EVM chains is still limited in this build."
        await m.edit_text(t, parse_mode='HTML')
    except Exception as e:
        await m.edit_text(f'❌ Risk check failed:\n<code>{html.escape(str(e)[:800])}</code>', parse_mode='HTML')


async def report(u, c):
    await analyze_cmd(u, c)


def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    if not token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured.')
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('analyze', analyze_cmd))
    app.add_handler(CommandHandler('holders', holders_cmd))
    app.add_handler(CommandHandler('risk', risk))
    app.add_handler(CommandHandler('report', report))
    app.add_handler(CallbackQueryHandler(cb, pattern=r'^(ha|hn|hp|hr):'))
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()