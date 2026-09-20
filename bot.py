import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from analysis import (
    analyze_token,
    format_analysis,
    format_holders,
)


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is missing."
    )


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("web3-oasis")


# ============================================================
# HELPERS
# ============================================================

def extract_address(
    update: Update,
) -> str | None:

    if not update.message:
        return None

    text = update.message.text or ""

    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        return None

    return parts[1].strip()


# ============================================================
# START
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
# HELP
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
        "Holder count, supply and top holders "
        "when explorer data is available.\n\n"
        "/risk <contract>\n"
        "Risk intelligence.\n\n"
        "/report <contract>\n"
        "Detailed project report.\n\n"
        "Example:\n"
        "/analyze 0x123..."
    )


# ============================================================
# ANALYZE
# ============================================================

async def analyze_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    address = extract_address(update)

    if not address:
        await update.message.reply_text(
            "Usage:\n"
            "/analyze <contract address>"
        )
        return

    status = await update.message.reply_text(
        "🔎 Detecting chain and analyzing contract..."
    )

    try:

        data = await analyze_token(address)

        result = format_analysis(data)

        await status.edit_text(result)

    except Exception:

        logger.exception(
            "Analysis error"
        )

        await status.edit_text(
            "❌ Something went wrong while "
            "analyzing that contract."
        )


# ============================================================
# HOLDERS
# ============================================================

async def holders_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    address = extract_address(update)

    if not address:
        await update.message.reply_text(
            "Usage:\n"
            "/holders <contract address>"
        )
        return

    status = await update.message.reply_text(
        "👥 Detecting chain and loading holder intelligence..."
    )

    try:

        data = await analyze_token(address)

        result = format_holders(data)

        await status.edit_text(
            result,
            parse_mode="Markdown",
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
# RISK
# ============================================================

async def risk_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    address = extract_address(update)

    if not address:
        await update.message.reply_text(
            "Usage:\n"
            "/risk <contract address>"
        )
        return

    await update.message.reply_text(
        "🛡️ Web3 Oasis Risk Engine\n\n"
        "The risk engine is being connected to "
        "the on-chain and holder intelligence layer."
    )


# ============================================================
# REPORT
# ============================================================

async def report_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    address = extract_address(update)

    if not address:
        await update.message.reply_text(
            "Usage:\n"
            "/report <contract address>"
        )
        return

    status = await update.message.reply_text(
        "📊 Building Web3 Oasis report..."
    )

    try:

        data = await analyze_token(address)

        result = format_analysis(data)

        await status.edit_text(result)

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

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Web3 Oasis bot is starting..."
    )

    application.run_polling()


if __name__ == "__main__":
    main()