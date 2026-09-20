import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from analysis import analyze_token, format_analysis


# =========================
# CONFIGURATION
# =========================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is not set in Railway Variables."
    )


# =========================
# LOGGING
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# /START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = (
        "🤖 *Web3 Oasis*\n\n"
        "Your Web3 intelligence bot is online.\n\n"
        "I can analyze crypto tokens using "
        "on-chain and market data.\n\n"
        "*Commands:*\n"
        "🔍 /analyze — Analyze a token\n"
        "⚠️ /risk — Risk analysis\n"
        "👥 /holders — Holder analysis\n"
        "📊 /report — Full report\n"
        "❓ /help — Show help\n\n"
        "Example:\n"
        "`/analyze 0xYourTokenAddress`"
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
    )


# =========================
# /HELP
# =========================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = (
        "📚 *Web3 Oasis Help*\n\n"
        "🔍 `/analyze <token>`\n"
        "Analyze market and on-chain data.\n\n"
        "⚠️ `/risk <token>`\n"
        "Check available risk indicators.\n\n"
        "👥 `/holders <token>`\n"
        "Check holder intelligence.\n\n"
        "📊 `/report <token>`\n"
        "Generate a broader report.\n\n"
        "Example:\n"
        "`/analyze 0x123...`"
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
    )


# =========================
# /ANALYZE
# =========================

async def analyze(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text(
            "🔍 Please provide a token contract address.\n\n"
            "Example:\n"
            "`/analyze 0x123...`",
            parse_mode="Markdown",
        )
        return

    token_address = context.args[0].strip()

    status_message = await update.message.reply_text(
        "🔎 Analyzing token...\n\n"
        "⛓️ Checking on-chain data\n"
        "📊 Checking market data\n"
        "🧠 Processing intelligence..."
    )

    try:
        result = await analyze_token(
            token_address
        )

        response = format_analysis(
            result
        )

        await status_message.edit_text(
            response,
            parse_mode="Markdown",
        )

    except Exception as exc:
        logger.exception(
            "Analysis failed: %s",
            exc,
        )

        await status_message.edit_text(
            "❌ Something went wrong while analyzing "
            "this token.\n\n"
            "Please check the contract address and "
            "try again."
        )


# =========================
# /RISK
# =========================

async def risk(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a token contract address.\n\n"
            "Example:\n"
            "`/risk 0x123...`",
            parse_mode="Markdown",
        )
        return

    token_address = context.args[0].strip()

    await update.message.reply_text(
        "⚠️ Risk analysis is being connected to the "
        "intelligence engine.\n\n"
        f"Token:\n`{token_address}`",
        parse_mode="Markdown",
    )


# =========================
# /HOLDERS
# =========================

async def holders(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text(
            "👥 Please provide a token contract address.\n\n"
            "Example:\n"
            "`/holders 0x123...`",
            parse_mode="Markdown",
        )
        return

    token_address = context.args[0].strip()

    await update.message.reply_text(
        "👥 Holder analysis is being connected to the "
        "intelligence engine.\n\n"
        f"Token:\n`{token_address}`",
        parse_mode="Markdown",
    )


# =========================
# /REPORT
# =========================

async def report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.message.reply_text(
            "📊 Please provide a token contract address.\n\n"
            "Example:\n"
            "`/report 0x123...`",
            parse_mode="Markdown",
        )
        return

    token_address = context.args[0].strip()

    status_message = await update.message.reply_text(
        "📊 Generating intelligence report...\n\n"
        "⛓️ On-chain data\n"
        "💧 Liquidity data\n"
        "📈 Market data\n"
        "🧠 Intelligence processing..."
    )

    try:
        result = await analyze_token(
            token_address
        )

        response = format_analysis(
            result
        )

        await status_message.edit_text(
            response,
            parse_mode="Markdown",
        )

    except Exception as exc:
        logger.exception(
            "Report generation failed: %s",
            exc,
        )

        await status_message.edit_text(
            "❌ Unable to generate the report right now."
        )


# =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "Telegram error:",
        exc_info=context.error,
    )


# =========================
# MAIN
# =========================

def main():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("analyze", analyze)
    )

    application.add_handler(
        CommandHandler("risk", risk)
    )

    application.add_handler(
        CommandHandler("holders", holders)
    )

    application.add_handler(
        CommandHandler("report", report)
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Web3 Oasis is starting..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()