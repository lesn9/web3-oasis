import os
import logging
import uuid

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from analysis import (
    analyze_token,
    format_analysis,
    format_holder_page,
    get_holder_page,
)


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is missing."
    )


logging.basicConfig(
    format=(
        "%(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger("web3-oasis")


# ============================================================
# HOLDER PAGINATION SESSIONS
# ============================================================

# Each Telegram holder message gets its own short session ID.
#
# Example:
#
# sessions["a91f2c"] = {
#     "user_id": 123456,
#     "message_id": 987,
#     "data": {...},
#     "chain": {...},
#     "address": "...",
#     "pages": [
#         None,
#         {...cursor for page 2...},
#         {...cursor for page 3...}
#     ],
#     "current_page": 0
# }

holder_sessions = {}


# ============================================================
# HELPERS
# ============================================================

def extract_address(
    update: Update,
) -> str | None:

    if not update.message:
        return None

    text = update.message.text or ""

    parts = text.split(
        maxsplit=1
    )

    if len(parts) < 2:
        return None

    return parts[1].strip()


def holder_keyboard(
    session_id: str,
    has_previous: bool,
    has_next: bool,
) -> InlineKeyboardMarkup:

    buttons = []

    if has_previous:
        buttons.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"hp:{session_id}:prev",
            )
        )

    if has_next:
        buttons.append(
            InlineKeyboardButton(
                "➡️ Next",
                callback_data=f"hp:{session_id}:next",
            )
        )

    if not buttons:
        buttons.append(
            InlineKeyboardButton(
                "End of holders",
                callback_data=f"hp:{session_id}:noop",
            )
        )

    return InlineKeyboardMarkup(
        [buttons]
    )


def cleanup_old_sessions():

    # Keep memory from growing forever.
    #
    # We only keep the newest 100 sessions.
    if len(holder_sessions) <= 100:
        return

    keys = list(holder_sessions.keys())

    for key in keys[:-100]:
        holder_sessions.pop(
            key,
            None,
        )


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🤖 Web3 Oasis\n\n"
        "Your multichain EVM intelligence bot.\n\n"
        "I automatically identify supported networks "
        "from contract addresses — you normally don't "
        "need to tell me the chain.\n\n"
        "Commands:\n"
        "/analyze <contract>\n"
        "/holders <contract>\n"
        "/risk <contract>\n"
        "/report <contract>\n"
        "/help"
    )


# ============================================================
# /HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🤖 Web3 Oasis Help\n\n"
        "/analyze <contract>\n"
        "Full token and market analysis.\n\n"
        "/holders <contract>\n"
        "Holder count, supply and paginated top holders.\n\n"
        "/risk <contract>\n"
        "Risk intelligence.\n\n"
        "/report <contract>\n"
        "Detailed project report.\n\n"
        "Example:\n"
        "/analyze 0x123..."
    )


# ============================================================
# /ANALYZE
# ============================================================

async def analyze_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    address = extract_address(update)

    if not address:
        await update.message.reply_text(
            "Usage:\n/analyze <contract address>"
        )
        return

    status = await update.message.reply_text(
        "🔎 Detecting chain and analyzing contract..."
    )

    try:

        data = await analyze_token(
            address
        )

        result = format_analysis(
            data
        )

        await status.edit_text(
            result
        )

    except Exception:

        logger.exception(
            "Analysis error"
        )

        await status.edit_text(
            "❌ Something went wrong while "
            "analyzing that contract."
        )


# ============================================================
# /HOLDERS
# ============================================================

async def holders_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    address = extract_address(update)

    if not address:
        await update.message.reply_text(
            "Usage:\n/holders <contract address>"
        )
        return

    status = await update.message.reply_text(
        "👥 Detecting chain and loading "
        "holder intelligence..."
    )

    try:

        data = await analyze_token(
            address
        )

        first_page = data["holders"]["first_page"]

        session_id = uuid.uuid4().hex[:8]

        holder_sessions[session_id] = {
            "user_id": update.effective_user.id,
            "message_id": status.message_id,
            "data": data,
            "chain": data["chain"],
            "address": data["address"],

            # Page 0 has no cursor.
            #
            # Page 1 cursor is obtained from the first
            # response and stored when Next is pressed.
            "pages": [
                None
            ],

            "current_page": 0,

            "next_page_params": (
                first_page.get(
                    "next_page_params"
                )
            ),
        }

        cleanup_old_sessions()

        result = format_holder_page(
            data=data,
            page_items=first_page.get(
                "items",
                [],
            ),
            page_number=1,
            has_previous=False,
            has_next=bool(
                first_page.get(
                    "next_page_params"
                )
            ),
        )

        keyboard = holder_keyboard(
            session_id=session_id,
            has_previous=False,
            has_next=bool(
                first_page.get(
                    "next_page_params"
                )
            ),
        )

        await status.edit_text(
            result,
            reply_markup=keyboard,
        )

    except Exception:

        logger.exception(
            "Holder analysis error"
        )

        await status.edit_text(
            "❌ Something went wrong while "
            "loading holder data."
        )


# ============================================================
# HOLDER PAGINATION CALLBACK
# ============================================================

async def holder_pagination(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query:
        return

    await query.answer()

    callback_data = query.data or ""

    parts = callback_data.split(":")

    if len(parts) != 3:
        return

    _, session_id, action = parts

    session = holder_sessions.get(
        session_id
    )

    if not session:
        await query.answer(
            "This holder session has expired. "
            "Run /holders again.",
            show_alert=True,
        )
        return

    if query.from_user.id != session["user_id"]:

        await query.answer(
            "This holder navigation belongs "
            "to another user.",
            show_alert=True,
        )

        return

    if action == "noop":
        return

    current_page = session[
        "current_page"
    ]

    pages = session[
        "pages"
    ]

    # --------------------------------------------------------
    # NEXT
    # --------------------------------------------------------

    if action == "next":

        next_cursor = session.get(
            "next_page_params"
        )

        if not next_cursor:

            await query.answer(
                "There are no more holders.",
                show_alert=True,
            )

            return

        next_page_number = (
            current_page + 1
        )

        try:

            result = await get_holder_page(
                session["chain"],
                session["address"],
                cursor=next_cursor,
            )

        except Exception:

            logger.exception(
                "Next holder page error"
            )

            await query.answer(
                "Could not load the next page.",
                show_alert=True,
            )

            return

        # Store the cursor used to reach this page.
        #
        # This lets Previous reconstruct the page.
        if len(pages) <= next_page_number:

            pages.append(
                dict(next_cursor)
            )

        else:

            pages[
                next_page_number
            ] = dict(next_cursor)

        session[
            "current_page"
        ] = next_page_number

        session[
            "next_page_params"
        ] = result.get(
            "next_page_params"
        )

    # --------------------------------------------------------
    # PREVIOUS
    # --------------------------------------------------------

    elif action == "prev":

        if current_page <= 0:

            await query.answer(
                "You're already on the first page.",
                show_alert=True,
            )

            return

        previous_page = (
            current_page - 1
        )

        # The cursor stored at pages[previous_page]
        # is the cursor that produced that page.
        previous_cursor = pages[
            previous_page
        ]

        try:

            result = await get_holder_page(
                session["chain"],
                session["address"],
                cursor=previous_cursor,
            )

        except Exception:

            logger.exception(
                "Previous holder page error"
            )

            await query.answer(
                "Could not load the previous page.",
                show_alert=True,
            )

            return

        session[
            "current_page"
        ] = previous_page

        session[
            "next_page_params"
        ] = result.get(
            "next_page_params"
        )

    else:
        return

    # --------------------------------------------------------
    # UPDATE MESSAGE
    # --------------------------------------------------------

    page_number = (
        session["current_page"] + 1
    )

    page_items = result.get(
        "items",
        [],
    )

    has_previous = (
        session["current_page"] > 0
    )

    has_next = bool(
        session.get(
            "next_page_params"
        )
    )

    text = format_holder_page(
        data=session["data"],
        page_items=page_items,
        page_number=page_number,
        has_previous=has_previous,
        has_next=has_next,
    )

    keyboard = holder_keyboard(
        session_id=session_id,
        has_previous=has_previous,
        has_next=has_next,
    )

    try:

        await query.edit_message_text(
            text,
            reply_markup=keyboard,
        )

    except Exception:

        logger.exception(
            "Could not update holder message"
        )


# ============================================================
# /RISK
# ============================================================

async def risk_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    address = extract_address(update)

    if not address:

        await update.message.reply_text(
            "Usage:\n/risk <contract address>"
        )

        return

    await update.message.reply_text(
        "🛡️ Web3 Oasis Risk Engine\n\n"
        "The risk engine is being connected "
        "to the on-chain and holder intelligence layer."
    )


# ============================================================
# /REPORT
# ============================================================

async def report_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    address = extract_address(update)

    if not address:

        await update.message.reply_text(
            "Usage:\n/report <contract address>"
        )

        return

    status = await update.message.reply_text(
        "📊 Building Web3 Oasis report..."
    )

    try:

        data = await analyze_token(
            address
        )

        result = format_analysis(
            data
        )

        await status.edit_text(
            result
        )

    except Exception:

        logger.exception(
            "Report error"
        )

        await status.edit_text(
            "❌ Something went wrong while "
            "building the report."
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.exception(
        "Telegram error",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "analyze",
            analyze_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "holders",
            holders_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "risk",
            risk_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "report",
            report_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            holder_pagination,
            pattern=r"^hp:",
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Web3 Oasis bot is starting..."
    )

    application.run_polling()


if __name__ == "__main__":
    main()