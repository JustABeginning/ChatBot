"""OpenAI Response based Telegram Bot"""

#!/usr/bin/env python

# Import Modules

import logging
import os
import sys
import threading
import time
import re
import asyncio
from datetime import datetime
import openai

from telegram import __version__ as TG_VER

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

completion = openai.Completion()

# Global Tokens

TELEGRAM_TOKEN = "TELEGRAM_API_KEY"
OPENAI_TOKEN = "OPENAI_API_KEY"

# OpenAI API key
aienv = os.getenv('OPENAI_KEY')
if aienv is None:
    openai.api_key = OPENAI_TOKEN
else:
    openai.api_key = aienv
print(aienv)

# Telegram bot key
tgenv = os.getenv('TELEGRAM_KEY')
if tgenv is None:
    TGKEY = TELEGRAM_TOKEN
else:
    TGKEY = tgenv
print(tgenv)

# Lots of console output
DEBUG = True

# User Session timeout
TIMSTART = 300
TIM = 1

# Defaults
USER = "user"
RUNNING = False
CACHE = None
QCACHE = None
CHAT_LOG = None
BOTNAME = 'botname'
USERNAME = 'username'
# Max chat log length (A token is about 4 letters and max tokens is 2048)
MAX = int(3000)

# Define a few command handlers. These usually take the two arguments update and
# context.


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    USER = update.effective_user
    global CHAT_LOG
    global QCACHE
    global CACHE
    global TIM
    left = str(TIM)
    if TIM == 1:
        CHAT_LOG = None
        CACHE = None
        QCACHE = None
        await update.message.reply_html(
            rf"Hi {USER.mention_html()}!",  # type: ignore
            reply_markup=ForceReply(selective=True),
        )
        return
    else:
        await update.message.reply_text(
            'I am currently talking to someone else. Can you please wait ' + left + ' seconds?'
        )
        return


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        '[/reset] resets the conversation,' +
        '\n [/retry] retries the last output,' +
        '\n [/username name] sets your name to the bot, default is "Human",' +
        '\n [/botname name] sets the bots character name, default is "AI"'
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /reset is issued."""
    global CHAT_LOG
    global CACHE
    global QCACHE
    left = str(TIM)
    if USER == update.message.from_user.id:
        CHAT_LOG = None
        CACHE = None
        QCACHE = None
        await update.message.reply_text('Bot has been reset, send a message!')
        return
    if TIM == 1:
        CHAT_LOG = None
        CACHE = None
        QCACHE = None
        await update.message.reply_text('Bot has been reset, send a message!')
        return
    else:
        await update.message.reply_text(
            'I am currently talking to someone else. Can you please wait ' + left + ' seconds?'
        )
        return


async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /retry is issued."""
    global CHAT_LOG
    global CACHE
    global QCACHE
    left = str(TIM)
    if USER == update.message.from_user.id:
        new = True
        compute = threading.Thread(target=wait_call, args=(
            update, new))
        compute.start()
        return
    if TIM == 1:
        CHAT_LOG = None
        CACHE = None
        QCACHE = None
        await update.message.reply_text('Send a message!')
        return
    else:
        await update.message.reply_text(
            'I am currently talking to someone else. Can you please wait ' + left + ' seconds?'
        )
        return


async def runn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when a message is received."""
    new = False
    global BOTNAME
    global USERNAME
    if "/botname " in update.message.text:
        try:
            string = update.message.text
            charout = string.split("/botname ", 1)[1]
            BOTNAME = charout
            response = "The bot character name set to: " + BOTNAME
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(str(e))
        return
    if "/username " in update.message.text:
        try:
            string = update.message.text
            userout = string.split("/username ", 1)[1]
            USERNAME = userout
            response = "Your character name set to: " + USERNAME
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(str(e))
        return
    else:
        compute = threading.Thread(target=interact_call, args=(
            update, new))
        compute.start()


async def wait(update, new):
    global USER
    global CHAT_LOG
    global CACHE
    global QCACHE
    global TIM
    global RUNNING
    if USER == "":
        USER = update.message.from_user.id
    if USER == update.message.from_user.id:
        TIM = TIMSTART
        compute = threading.Thread(
            target=interact_call, args=(update, new))
        compute.start()
        if RUNNING is False:
            while TIM > 1:
                RUNNING = True
                time.sleep(1)
                TIM = TIM - 1
        if RUNNING is True:
            CHAT_LOG = None
            CACHE = None
            QCACHE = None
            await update.message.reply_text('Timer has run down, bot has been reset to defaults.')
            RUNNING = False
    else:
        left = str(TIM)
        await update.message.reply_text(
            'I am currently talking to someone else. Can you please wait ' + left + ' seconds?'
        )


def wait_call(update, new):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(wait(update, new))


################
# Main functions #
################


def limit(text):
    if (len(text) >= MAX):
        inv = MAX * 10
        print("Reducing length of chat history... This can be a bit buggy.")
        nl = text[inv:]
        text = re.search(r'(?<=\n)[\s\S]*', nl).group(0)  # type: ignore
        return text
    else:
        return text


def append_interaction_to_chat_log(question, answer, chat_log=None):
    if chat_log is None:
        chat_log = 'The following is a chat between two users:\n\n'
    chat_log = limit(chat_log)
    now = datetime.now()
    ampm = now.strftime("%I:%M %p")
    t = '[' + ampm + '] '
    return f'{chat_log}{t}{USERNAME}: {question}\n{t}{BOTNAME}: {answer}\n'


def ask(question, chat_log=None):
    if chat_log is None:
        chat_log = 'The following is a chat between two users:\n\n'
    now = datetime.now()
    ampm = now.strftime("%I:%M %p")
    t = '[' + ampm + '] '
    prompt = f'{chat_log}{t}{USERNAME}: {question}\n{t}{BOTNAME}:'
    response = completion.create(prompt=prompt, engine="text-davinci-003",
                                 temperature=0.5, frequency_penalty=0.5,
                                 presence_penalty=0.5, best_of=3, max_tokens=500)
    answer = response.choices[0].text.strip()  # type: ignore
    return answer
    # fp = 15 pp= 1 top_p = 1 temp = 0.9


async def interact(update, new):
    global CHAT_LOG
    global CACHE
    global QCACHE
    print("\n==========START==========\n")
    tex = update.message.text
    text = str(tex)
    if new is True:
        if DEBUG is True:
            print("Chat_Log CACHE is...")
            print(CACHE)
            print("Question CACHE is...")
            print(QCACHE)
        CHAT_LOG = CACHE
        question = QCACHE
    else:
        question = text
        QCACHE = question
        CACHE = CHAT_LOG
    # update.message.reply_text('Computing...')
    try:
        answer = ask(question, CHAT_LOG)
        if DEBUG is True:
            print("Input :\n" + question)  # type: ignore
            print("\nOutput :\n" + answer)  # type: ignore
            print("\n====================\n")
        await update.message.reply_text(answer)
        CHAT_LOG = append_interaction_to_chat_log(
            question, answer, CHAT_LOG)  # type: ignore
        if DEBUG is True:
            # Print the chat log for debugging
            print('-----PRINTING CHAT LOG-----\n')
            print(CHAT_LOG)
            print('-----END CHAT LOG-----\n')
    except Exception as e:
        errstr = str(e)
        print('\nException ::\n' + errstr)
        await update.message.reply_text(errstr)


def interact_call(update, new):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(interact(update, new))


async def error(update: Update):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused ERROR !', update)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("retry", retry))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, runn))

    # on non command i.e message - echo the message on Telegram
    #    application.add_handler(MessageHandler(
    #        filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
