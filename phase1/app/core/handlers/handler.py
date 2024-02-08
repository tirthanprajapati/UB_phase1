import asyncio

from pyrogram.types import Message as Msg

from app import BOT, Config, Message, bot
from app.core.handlers import filters


@bot.on_message(
    filters.owner_filter | filters.super_user_filter | filters.sudo_filter, group=1
)
@bot.on_edited_message(
    filters.owner_filter | filters.super_user_filter | filters.sudo_filter, group=1
)
async def cmd_dispatcher(bot: BOT, message: Message) -> None:
    message = Message.parse(message)
    func = Config.CMD_DICT[message.cmd].func
    task = asyncio.Task(func(bot, message), name=message.task_id)
    try:
        await task
        if message.is_from_owner:
            await message.delete()
    except asyncio.exceptions.CancelledError:
        await bot.log_text(text=f"<b>#Cancelled</b>:\n<code>{message.text}</code>")
    except Exception as e:
        bot.log.error(e, exc_info=True, extra={"tg_message": message})
    message.stop_propagation()


@bot.on_message(filters.convo_filter, group=0)
@bot.on_edited_message(filters.convo_filter, group=0)
async def convo_handler(bot: BOT, message: Msg):
    conv_obj: bot.Convo = bot.Convo.CONVO_DICT[message.chat.id]
    if conv_obj.filters and not (await conv_obj.filters(bot, message)):
        message.continue_propagation()
    conv_obj.responses.append(message)
    conv_obj.response.set_result(message)
    message.continue_propagation()
