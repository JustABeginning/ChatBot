#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

# Import Modules

import logging

from telegram import Bot, __version__ as TG_VER

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
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
import os
import sys
import threading
import time
import re
import openai
import asyncio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

completion = openai.Completion()

# Global Tokens

telegram_token = "Paste TELEGRAM_KEY"
openai_token = "Paste OPENAI_KEY"

# OpenAI API key
aienv = os.getenv('OPENAI_KEY')
if aienv == None:
    openai.api_key = openai_token
else:
    openai.api_key = aienv
print(aienv)

# Telegram bot key
tgenv = os.getenv('TELEGRAM_KEY')
if tgenv == None:
    tgkey = telegram_token
else:
    tgkey = tgenv
print(tgenv)

# Lots of console output
debug = True

# User Session timeout
timstart = 300
tim = 1

# Defaults
user = "<user>"
running = False
cache = None
qcache = None
chat_log = None
botname = '<botname>'
username = '<username>'
# Max chat log length (A token is about 4 letters and max tokens is 2048)
max = int(3000)

# Define a few command handlers. These usually take the two arguments update and
# context.


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    global chat_log
    global qcache
    global cache
    global tim
    global botname
    global username
    left = str(tim)
    if tim == 1:
        chat_log = None
        cache = None
        qcache = None
        botname = '<botname>'
        username = '<username>'
        await update.message.reply_html(
            rf"Hi {user.mention_html()}!",  # type: ignore
            reply_markup=ForceReply(selective=True),
        )
        return
    else:
        await update.message.reply_text('I am currently talking to someone else. Can you please wait ' + left + ' seconds?')
        return


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text('[/reset] resets the conversation,\n [/retry] retries the last output,\n [/username name] sets your name to the bot, default is "Human",\n [/botname name] sets the bots character name, default is "AI"')


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /reset is issued."""
    global chat_log
    global cache
    global qcache
    global tim
    global botname
    global username
    left = str(tim)
    if user == update.message.from_user.id:
        chat_log = None
        cache = None
        qcache = None
        botname = '<botname>'
        username = '<username>'
        await update.message.reply_text('Bot has been reset, send a message!')
        return
    if tim == 1:
        chat_log = None
        cache = None
        qcache = None
        botname = '<botname>'
        username = '<username>'
        await update.message.reply_text('Bot has been reset, send a message!')
        return
    else:
        await update.message.reply_text('I am currently talking to someone else. Can you please wait ' + left + ' seconds?')
        return


async def retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /retry is issued."""
    global chat_log
    global cache
    global qcache
    global tim
    global botname
    global username
    left = str(tim)
    if user == update.message.from_user.id:
        new = True
        comput = threading.Thread(target=wait_call, args=(
            update, botname, username, new,))
        comput.start()
        return
    if tim == 1:
        chat_log = None
        cache = None
        qcache = None
        botname = '<botname>'
        username = '<username>'
        await update.message.reply_text('Send a message!')
        return
    else:
        await update.message.reply_text('I am currently talking to someone else. Can you please wait ' + left + ' seconds?')
        return


async def runn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when a message is received."""
    new = False
    global botname
    global username
    if "/botname " in update.message.text:
        try:
            string = update.message.text
            charout = string.split("/botname ", 1)[1]
            botname = charout
            response = "The bot character name set to: " + botname
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(str(e))
        return
    if "/username " in update.message.text:
        try:
            string = update.message.text
            userout = string.split("/username ", 1)[1]
            username = userout
            response = "Your character name set to: " + username
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(str(e))
        return
    else:
        comput = threading.Thread(target=interact_call, args=(
            update, botname, username, new,))
        comput.start()


async def wait(update, botname, username, new):
    global user
    global chat_log
    global cache
    global qcache
    global tim
    global running
    if user == "":
        user = update.message.from_user.id
    if user == update.message.from_user.id:
        tim = timstart
        compute = threading.Thread(
            target=interact_call, args=(update, botname, username, new,))
        compute.start()
        if running == False:
            while tim > 1:
                running = True
                time.sleep(1)
                tim = tim - 1
        if running == True:
            chat_log = None
            cache = None
            qcache = None
            user = "<user>"
            username = '<username>'
            botname = '<botname>'
            await update.message.reply_text('Timer has run down, bot has been reset to defaults.')
            running = False
    else:
        left = str(tim)
        await update.message.reply_text('I am currently talking to someone else. Can you please wait ' + left + ' seconds?')


def wait_call(update, botname, username, new):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(wait(update, botname, username, new))


################
# Main functions #
################


def limit(text, max):
    if (len(text) >= max):
        inv = max * 10
        print("Reducing length of chat history... This can be a bit buggy.")
        nl = text[inv:]
        text = re.search(r'(?<=\n)[\s\S]*', nl).group(0)  # type: ignore
        return text
    else:
        return text


def append_interaction_to_chat_log(username, botname, question, answer, chat_log=None):
    if chat_log is None:
        chat_log = 'The following is a chat between two users:\n\n'
    chat_log = limit(chat_log, max)
    now = datetime.now()
    ampm = now.strftime("%I:%M %p")
    t = '[' + ampm + '] '
    return f'{chat_log}{t}{username}: {question}\n{t}{botname}: {answer}\n'


def ask(username, botname, question, chat_log=None):
    if chat_log is None:
        chat_log = 'The following is a chat between two users:\n\n'
    now = datetime.now()
    ampm = now.strftime("%I:%M %p")
    t = '[' + ampm + '] '
    prompt = f'{chat_log}{t}{username}: {question}\n{t}{botname}:'
    response = completion.create(prompt=prompt, engine="text-curie-001", stop=[
                                 '\n'], temperature=0.7, top_p=1, frequency_penalty=0, presence_penalty=0.6, best_of=3, max_tokens=500)
    answer = response.choices[0].text.strip()  # type: ignore
    return answer
    # fp = 15 pp= 1 top_p = 1 temp = 0.9


async def interact(update, botname, username, new):
    global chat_log
    global cache
    global qcache
    print("==========START==========")
    tex = update.message.text
    text = str(tex)
    analyzer = SentimentIntensityAnalyzer()
    if new != True:
        vs = analyzer.polarity_scores(text)
        if debug == True:
            print("Sentiment of input:\n")
            print(vs)
        if vs['neg'] > 1:
            await update.message.reply_text('Can we talk something else?')
            return
    if new == True:
        if debug == True:
            print("Chat_LOG Cache is...")
            print(cache)
            print("Question Cache is...")
            print(qcache)
        chat_log = cache
        question = qcache
    else:
        question = text
        qcache = question
        cache = chat_log
    # update.message.reply_text('Computing...')
    try:
        answer = ask(username, botname, question, chat_log)
        if debug == True:
            print("Input:\n" + question)  # type: ignore
            print("Output:\n" + answer)  # type: ignore
            print("====================")
        stripes = answer.encode(  # type: ignore
            encoding=sys.stdout.encoding, errors='ignore')
        decoded = stripes.decode("utf-8")
        out = str(decoded)
        vs = analyzer.polarity_scores(out)
        if debug == True:
            print("Sentiment of output:\n")
            print(vs)
        if vs['neg'] > 1:
            await update.message.reply_text('I do not think I could provide you a good answer for this. Use /retry to get positive output.')
            return
        update.message.reply_text(out)
        chat_log = append_interaction_to_chat_log(
            username, botname, question, answer, chat_log)  # type: ignore
        if debug == True:
            # Print the chat log for debugging
            print('-----PRINTING CHAT LOG-----')
            print(chat_log)
            print('-----END CHAT LOG-----')
    except Exception as e:
        print(e)
        errstr = str(e)
        await update.message.reply_text(errstr)


def interact_call(update, botname, username, new):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(interact(update, botname, username, new))


async def error(update: Update):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(telegram_token).build()

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
