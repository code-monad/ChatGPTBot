import asyncio
import atexit
import csv
import html
import logging
import traceback

import telegram.constants
import toml
from emoji import emojize
from loguru import logger
from revChatGPT.revChatGPT import AsyncChatbot as Chatbot
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, \
    CallbackQueryHandler

import nest_asyncio
import memories

config_file = "config.toml"
memory_file = "memories.sav"
in_Debug = True
inited = False
in_naming = False
memory_map = {}
unnamed_memory = None
last_reply = None
last_chat = ""

chatbot = None
config = {}
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)
    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    if len(tb_string) > 4000:
        tb_string = tb_string[:4000]

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=message, parse_mode=telegram.constants.ParseMode.HTML
    )


async def check_id(userid, context):
    if userid not in config_map["bot"]["allow"]:
        await context.bot.send_message(
            chat_id=userid, text="你没有权限"
        )
        return True


async def chat_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_id(update.effective_chat.id, context):
        return
    if chatbot is not None:
        msg = "coversation_id:{}, parent_id:{}".format(chatbot.conversation_id, chatbot.parent_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def list_memories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_id(update.effective_chat.id, context):
        return
    global memory_map
    if len(memory_map) > 0:
        keyboard = []
        for name in memory_map:
            keyboard.append([InlineKeyboardButton(f"{name}: conversation_id:{memory_map[name].conversation_id}, parent_id{memory_map[name].parent_id}", callback_data=f"/load {name}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(chat_id=update.effective_chat.id, text="回忆列表如下", reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="没有保存过的记忆")

async def reroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_id(update.effective_chat.id, context):
        return
    if last_reply is not None and last_chat != "":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)
        await last_reply.edit_text("正在重新生成...")
        reply = await chatbot.get_chat_response(last_chat)
        reply_msg = reply["message"].encode().decode('utf-8')
        logger.info("Got reply: {}", reply_msg)
        await last_reply.edit_text(reply_msg)
        await update.message.delete() # Delete command log for better experience
    else:
        return


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_id(update.effective_chat.id, context):
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=telegram.constants.ChatAction.TYPING)
    keyboard = [
        [
            KeyboardButton("/list")
        ],
        [
            KeyboardButton("/check")
        ],
        [
            KeyboardButton("/reborn")
        ]
    ]
    markup = ReplyKeyboardMarkup(keyboard)
    start_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text="正在初始化……", reply_markup=markup)
    global chatbot, inited
    logger.debug(config)
    if chatbot is None:
        try:
            chatbot = Chatbot(config, conversation_id=None)
            inited = True
        except Exception as e:
            inited = False
            await update.message.reply_text(emojize(":sweat_drops:初始化失败！ 原因： `{}` ".format(e)),
                                            parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)
    else:
        inited = True

    if inited:
        keyboard = [
            [
                InlineKeyboardButton(emojize(":speech_balloon:开始新对话"), callback_data="/chat"),
                InlineKeyboardButton(emojize(":thought_balloon:继续旧对话"), callback_data="/list"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(emojize(":sparkles:已初始化"), reply_markup=reply_markup)
    await start_msg.delete()


async def reborn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_id(update.effective_chat.id, context):
        return
    if chatbot is not None:
        keyboard = [
            [
                InlineKeyboardButton(emojize(":speech_balloon:是"), callback_data=f"/save_this"),
                InlineKeyboardButton(emojize(":thought_balloon:否"), callback_data="/forget_this"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="你希望我保存这次回忆吗？",
                                       reply_markup=reply_markup)
    msg2 = await context.bot.send_message(chat_id=update.effective_chat.id, text="正在重置记忆…")
    if chatbot is not None:
        global unnamed_memory
        unnamed_memory = memories.GPTMemory(f"回忆#{len(memory_map)}", chatbot.conversation_id, chatbot.parent_id)
        chatbot.reset_chat()
        await msg2.edit_text("已初始化…！")
        await msg2.delete()

async def load(update: Update, context: ContextTypes.DEFAULT_TYPE, name):
    if await check_id(update.effective_chat.id, context):
        return
    if name in memory_map:
        if chatbot is not None:
            msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=f"正在加载记忆{name}...")
            chatbot.conversation_id = memory_map[name].conversation_id
            chatbot.parent_id = memory_map[name].parent_id
            await msg.edit_text("加载成功！")
            await asyncio.sleep(1)
            msg.delete()
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"没有名为{name}的记忆！")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_id(update.effective_chat.id, context):
        return
    if update.message is None or update.message.text is None or update.message.text == "":
        return
    logger.info("received: {}", update.message.text)
    global in_naming
    if in_naming:
        global unnamed_memory, memory_map
        if unnamed_memory is not None:
            try:
                unnamed_memory.name = update.message.text
                memory_map[update.message.text] = unnamed_memory
                unnamed_memory = None
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text="成功命名为{}".format(update.message.text))
                in_naming = False
            except Exception as e:
                logger.error("命名失败:{}", e)

    elif chatbot is not None:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                           action=telegram.constants.ChatAction.TYPING)
        reply = await chatbot.get_chat_response(update.message.text)
        reply_msg = reply["message"].encode().decode('utf-8')
        logger.info("Got reply: {}", reply_msg)
        global last_reply
        global last_chat
        last_chat = update.message.text
        last_reply = await context.bot.send_message(chat_id=update.effective_chat.id, text=reply_msg)


async def rollback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_id(update.effective_chat.id, context):
        return
    msg = await context.bot.send_message(chat_id=update.effective_chat.id, text="正在忘记上一条...")
    try:
        chatbot.rollback_conversation(1)
        msg.edit_text("已删除！")
        await msg.delete()
    except Exception as e:
        logger.error(e)


async def refresh_session(context: ContextTypes.DEFAULT_TYPE):
    try:
        if chatbot is not None:
            chatbot.refresh_session()
            config_map["chatgpt"]["session_token"] = chatbot.config["session_token"]
            config_map["chatgpt"]["cf_clearance"] = chatbot.config["cf_clearance"]
    except Exception as e:
        logger.error(e)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()
    await query.edit_message_text(text=f"指令: {query.data}")
    command = query.data.split()[0]
    match command:
        case "/save_this":
            global in_naming
            in_naming = True
            await context.bot.send_message(chat_id=update.effective_chat.id, text="请输入回忆的名字：")

        case "/forgot_this":
            await chat(update, context)

        case "/chat":
            await chat(update, context)

        case "/load":
            await load(update, context, query.data.split()[1])


        case "/list":
            await list_memories(update, context)

    await asyncio.sleep(1)
    await query.delete_message()


def save_datas():
    logger.info("Saving datas...")
    logger.info("Updating memories..")
    with open(memory_file, "w") as f:
        writer = csv.writer(f)
        for name in memory_map:
            writer.writerow([name, memory_map[name].conversation_id, memory_map[name].parent_id])
    logger.info("Updating Session keys...")
    if chatbot is not None:
        config_map["chatgpt"]["session_token"] = chatbot.config["session_token"]
        config_map["chatgpt"]["cf_clearance"] = chatbot.config["cf_clearance"]
        logger.info(config_map)
        with open(config_file, "w") as f:
            toml.dump(config_map, f)


if __name__ == '__main__':
    atexit.register(save_datas)
    nest_asyncio.apply()
    config_map = toml.load(config_file)
    logger.debug("Load from {}...".format(config_file))
    proxy_url = ""
    if "proxy" in config_map and "server" in config_map["proxy"]:
        proxy_url = config_map["proxy"]["server"]
    if config_map is None:
        logger.warning("")
    elif in_Debug:
        logger.debug("Telegram Bot token: {}", config_map["bot"]["token"])
        logger.debug("Allowed users' ID: {}", config_map["bot"]["allow"])
    config = {
        "session_token": config_map["chatgpt"]["session_token"],
        "cf_clearance": config_map["chatgpt"]["cf_clearance"],
        "user_agent": config_map["chatgpt"]["user_agent"]
    }
    logger.info(f"Loading memories from {memory_file}")
    memory_map = memories.LoadMemories(memory_file)
    logger.info(f"Memories:{memory_map}")
    builder = ApplicationBuilder().token(config_map["bot"]["token"])
    if proxy_url is not None and proxy_url != "":
        builder = builder.proxy_url(proxy_url).get_updates_proxy_url(proxy_url)
        config["proxy"] = proxy_url
    application = builder.build()

    start_handler = CommandHandler('start', start)
    reborn_handler = CommandHandler('reborn', reborn)
    list_handler = CommandHandler('list', list_memories)

    rollback_handler = CommandHandler('rollback', rollback)
    reroll_handler = CommandHandler('reroll', reroll)
    chat_handler = telegram.ext.MessageHandler(filters.TEXT & (~filters.COMMAND), chat)
    detail_handler = CommandHandler('check', chat_detail)

    application.add_handler(start_handler)
    application.add_handler(reborn_handler)
    application.add_handler(list_handler)
    application.add_handler(rollback_handler)
    application.add_handler(reroll_handler)
    application.add_handler(chat_handler)
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(detail_handler)
    application.add_error_handler(error_handler)
    application.job_queue.run_repeating(refresh_session, interval=20 * 60, first=20 * 60)

    application.run_polling()
