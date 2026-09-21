import os, asyncio, uuid, html
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
        '/report <code>address</code>',
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
                    p = markets[0]
                    liq = (p.get('liquidity') or {}).get('usd')
                    t += (
                        f"\n📊 <b>Market Data</b>\n"
                        f"• Pair: {html.escape((p.get('baseToken') or {}).get('symbol','?'))}/"
                        f"{html.escape((p.get('quoteToken') or {}).get('symbol','?'))}\n"
                        f"• DEX: {html.escape(p.get('dexId','?'))}\n"
                        f"• Price: ${p.get('priceUsd','?')}\n"
                        f"• Liquidity: ${liq if liq is not None else '?'}\n"
                        f"• 24h Volume: ${((p.get('volume') or {}).get('h24')) if (p.get('volume') or {}).get('h24') is not None else '?'}\n"
                        f"• 24h Change: {((p.get('priceChange') or {}).get('h24')) if (p.get('priceChange') or {}).get('h24') is not None else '?'}%\n"
                        f"🔗 {html.escape(p.get('url',''))}\n"
                    )
                else:
                    t += '\n📊 <b>Market Data</b>\n• No indexed DexScreener pair found.\n'
                await u.message.reply_text(t, parse_mode='HTML', disable_web_page_preview=True)
            await m.delete()
            return

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
        if r.get('total_holders') is not None:
            t += f"👥 Total Holders: <b>{r['total_holders']}</b>\n"
        if r.get('note'):
            t += f"\nℹ️ {html.escape(r['note'])}"

        if r.get('family') == 'solana' and r.get('holders'):
            t += '\n\n🏆 <b>Top Holders</b>\n'
            for i, x in enumerate(r['holders'][:10], 1):
                owner = x.get('owner') or ''
                line = f"{i}. <code>{html.escape(x.get('address',''))}</code> — {x.get('value','0')}"
                if owner:
                    line += f"\n   └ owner: <code>{html.escape(owner)}</code>"
                t += line + "\n"
            t += "\n👉 Run /holders to page through the full list."

        if r.get('family') == 'sui' and r.get('total_holders'):
            t += "\n👉 Run /holders to page through the full Sui holder list."

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
                    '⚠️ This address is detected on multiple supported EVM chains. '
                    'I need one unambiguous chain before building the holder list.'
                )
            ch = matches[0]
            await m.edit_text(
                f"⏳ Building the holder snapshot for <b>{html.escape(ch['name'])}</b>…\n\n"
                "This scans the token's indexed ERC-20 transfer history and calculates current non-zero balances."
                "\nIt may take a little longer for tokens with many transfers.",
                parse_mode='HTML'
            )
            data = await asyncio.wait_for(compute_evm_holders(a, ch), 180)
            if not data['items']:
                return await m.edit_text(
                    '⚠️ No non-zero holders were derived from the token transfer history. '
                    'That can mean the token has no indexed ERC-20 transfers or uses a non-standard transfer mechanism.'
                )
            sid = uuid.uuid4().hex[:10]
            SESSIONS[sid] = {
                'family': 'evm', 'address': a, 'chain': ch,
                'items': data['items'], 'page': 0,
                'total': data['total'], 'source': data['source'],
                'symbol': ch.get('symbol') or data['meta'].get('symbol',''),
                'decimals': data['meta'].get('decimals',18)
            }
            await m.delete()
            await render(u, sid)
            return

        if r.get('family') == 'solana':
            await m.edit_text('⏳ Loading Solana holder accounts from Alchemy…')
            items = r.get('holders') or []
            if not items:
                return await m.edit_text('⚠️ No token accounts returned for this mint.')
            sid = uuid.uuid4().hex[:10]
            SESSIONS[sid] = {
                'family': 'solana', 'address': a,
                'items': items, 'page': 0,
                'total': r.get('total_holders'),
                'chain': {'name': 'Solana'},
                'source': 'Alchemy getTokenAccounts',
                'symbol': r.get('symbol') or 'SPL Token',
            }
            await m.delete()
            await render(u, sid)
            return

        if r.get('family') == 'sui':
            await m.edit_text('⏳ Loading Sui holder index from BlockVision…')
            data = await asyncio.wait_for(sui_holders(a), 60)
            if data.get('needs_key'):
                return await m.edit_text(
                    'ℹ️ Sui token holders require a BlockVision API key.\n\n'
                    'Set <code>BLOCKVISION_API_KEY</code> in Railway to enable the Sui holder list.\n\n'
                    f"Coin type: <code>{html.escape(data['coin_type'])}</code>",
                    parse_mode='HTML'
                )
            if not data.get('items'):
                return await m.edit_text('⚠️ The Sui holder index returned no holder records.')
            sid = uuid.uuid4().hex[:10]
            SESSIONS[sid] = {
                'family': 'sui', 'address': a, 'coin_type': data['coin_type'],
                'items': data['items'], 'page': 0, 'total': data.get('total'),
                'chain': {'name': 'Sui'}, 'source': 'BlockVision'
            }
            await m.delete()
            await render(u, sid)
            return

        await m.edit_text(
            '⚠️ Holder pagination is implemented for EVM, Solana, and Sui tokens. '
            'TRON and TON are not yet supported.'
        )
    except Exception as e:
        await m.edit_text(
            f'❌ Holder lookup failed:\n<code>{html.escape(str(e)[:1200])}</code>',
            parse_mode='HTML'
        )


def holder_text(sid):
    s = SESSIONS.get(sid)
    if not s: return None
    page = s['page']; start = page * 10; end = min(start + 10, len(s['items']))
    visible = s['items'][start:end]
    total = s.get('total')

    if s['family'] == 'evm':
        title = f"🪙 {html.escape(s['symbol'] or 'Token')}"
        chain = html.escape(s['chain']['name'])
    elif s['family'] == 'solana':
        title = f"🪙 {html.escape(s.get('symbol') or 'SPL Token')