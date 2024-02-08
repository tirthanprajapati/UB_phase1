import asyncio

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.types import Chat, User

from app import BOT, Config, CustomDB, Message, bot
from app.utils.helpers import get_name

DB = CustomDB("FED_LIST")

BASIC_FILTER = filters.user([609517172, 2059887769]) & ~filters.service

FBAN_REGEX = filters.regex(
    r"(New FedBan|"
    r"starting a federation ban|"
    r"Starting a federation ban|"
    r"start a federation ban|"
    r"FedBan Reason update|"
    r"FedBan reason updated|"
    r"Would you like to update this reason)"
)


UNFBAN_REGEX = filters.regex(r"(New un-FedBan|I'll give|Un-FedBan)")


@bot.add_cmd(cmd="addf")
async def add_fed(bot: BOT, message: Message):
    """
    CMD: ADDF
    INFO: Add a Fed Chat to DB.
    USAGE:
        .addf | .addf NAME
    """
    data = dict(name=message.input or message.chat.title, type=str(message.chat.type))
    await DB.add_data({"_id": message.chat.id, **data})
    text = f"#FBANS\n<b>{data['name']}</b>: <code>{message.chat.id}</code> added to FED LIST."
    await message.reply(
        text=text,
        del_in=5,
        block=True,
    )
    await bot.log_text(text=text, type="info")


@bot.add_cmd(cmd="delf")
async def remove_fed(bot: BOT, message: Message):
    """
    CMD: DELF
    INFO: Delete a Fed from DB.
    FLAGS: -all to delete all feds.
    USAGE:
        .delf | .delf id | .delf -all
    """
    if "-all" in message.flags:
        await DB.drop()
        await message.reply("FED LIST cleared.")
        return
    chat: int | str | Chat = message.input or message.chat
    name = ""
    if isinstance(chat, Chat):
        name = f"Chat: {chat.title}\n"
        chat = chat.id
    elif chat.lstrip("-").isdigit():
        chat = int(chat)
    deleted: bool | None = await DB.delete_data(id=chat)
    if deleted:
        text = f"#FBANS\n<b>{name}</b><code>{chat}</code> removed from FED LIST."
        await message.reply(
            text=text,
            del_in=8,
            block=True,
        )
        await bot.log_text(text=text, type="info")
    else:
        await message.reply(f"<b>{name or chat}</b> not in FED LIST.", del_in=8)


@bot.add_cmd(cmd=["fban", "fbanp"])
async def fed_ban(bot: BOT, message: Message):
    progress: Message = await message.reply("❯")
    user, reason = await message.extract_user_n_reason()
    if isinstance(user, str):
        await progress.edit(user)
        return
    if not isinstance(user, User):
        user_id = user
        user_mention = f"<a href='tg://user?id={user_id}'>{user_id}</a>"
    else:
        user_id = user.id
        user_mention = user.mention
    if user_id in [Config.OWNER_ID, *Config.SUDO_USERS, *Config.SUDO_USERS]:
        await progress.edit("Cannot Fban Owner/Sudo users.")
        return
    proof_str: str = ""
    if message.cmd == "fbanp":
        if not message.replied:
            await message.reply("Reply to a proof")
            return
        proof = await message.replied.forward(Config.FBAN_LOG_CHANNEL)
        proof_str = f"\n{ {proof.link} }"

    reason = f"{reason}{proof_str}"

    if message.replied and not message.chat.type == ChatType.PRIVATE:
        me = await bot.get_chat_member(chat_id=message.chat.id, user_id="me")
        if me.status in {ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR}:
            await message.replied.reply(
                text=f"!dban {reason}",
                disable_web_page_preview=True,
                del_in=3,
                block=False,
            )

    await progress.edit("❯❯")
    total: int = 0
    failed: list[str] = []
    fban_cmd: str = f"/fban <a href='tg://user?id={user_id}'>{user_id}</a> {reason}"
    async for fed in DB.find():
        chat_id = int(fed["_id"])
        total += 1
        cmd: Message = await bot.send_message(
            chat_id=chat_id, text=fban_cmd, disable_web_page_preview=True
        )
        response: Message | None = await cmd.get_response(
            filters=BASIC_FILTER, timeout=8
        )
        if not response or not (await FBAN_REGEX(bot, response)):  # NOQA
            failed.append(fed["name"])
        elif "Would you like to update this reason" in response.text:
            await response.click("Update reason")
        await asyncio.sleep(1)
    if not total:
        await progress.edit("You Don't have any feds connected!")
        return
    resp_str = (
        f"❯❯❯ <b>FBanned</b> {user_mention}"
        f"\n<b>ID</b>: {user_id}"
        f"\n<b>Reason</b>: {reason}"
        f"\n<b>Initiated in</b>: {message.chat.title or 'PM'}"
    )
    if failed:
        resp_str += f"\n<b>Failed</b> in: {len(failed)}/{total}\n• " + "\n• ".join(
            failed
        )
    else:
        resp_str += f"\n<b>Status</b>: Fbanned in <b>{total}</b> feds."
    if not message.is_from_owner:
        resp_str += f"\n\n<b>By</b>: {get_name(message.from_user)}"
    await bot.send_message(
        chat_id=Config.FBAN_LOG_CHANNEL, text=resp_str, disable_web_page_preview=True
    )
    await progress.edit(
        text=resp_str, del_in=5, block=True, disable_web_page_preview=True
    )


@bot.add_cmd(cmd="unfban")
async def un_fban(bot: BOT, message: Message):
    progress: Message = await message.reply("❯")
    user, reason = await message.extract_user_n_reason()
    if isinstance(user, str):
        await progress.edit(user)
        return
    if not isinstance(user, User):
        user_id = user
        user_mention = f"<a href='tg://user?id={user_id}'>{user_id}</a>"
    else:
        user_id = user.id
        user_mention = user.mention

    await progress.edit("❯❯")
    total: int = 0
    failed: list[str] = []
    unfban_cmd: str = f"/unfban <a href='tg://user?id={user_id}'>{user_id}</a> {reason}"
    async for fed in DB.find():
        chat_id = int(fed["_id"])
        total += 1
        cmd: Message = await bot.send_message(
            chat_id=chat_id, text=unfban_cmd, disable_web_page_preview=True
        )
        response: Message | None = await cmd.get_response(
            filters=BASIC_FILTER, timeout=8
        )
        if not response or not (await UNFBAN_REGEX(bot, response)):
            failed.append(fed["name"])
        await asyncio.sleep(1)
    if not total:
        await progress.edit("You Don't have any feds connected!")
        return
    resp_str = (
        f"❯❯❯ <b>Un-FBanned {user_mention}" f"\nID: {user_id}" f"\nReason: {reason}\n"
    )
    if failed:
        resp_str += f"Failed in: {len(failed)}/{total}\n• " + "\n• ".join(failed)
    else:
        resp_str += f"Success! Un-Fbanned in {total} feds."
    await bot.send_message(
        chat_id=Config.FBAN_LOG_CHANNEL, text=resp_str, disable_web_page_preview=True
    )
    await progress.edit(
        text=resp_str, del_in=8, block=False, disable_web_page_preview=True
    )


@bot.add_cmd(cmd="listf")
async def fed_list(bot: BOT, message: Message):
    """
    CMD: LISTF
    INFO: View Connected Feds.
    FLAGS: -id to list Fed Chat IDs.
    USAGE: .listf | .listf -id
    """
    output: str = ""
    total = 0
    async for fed in DB.find():
        output += f'<b>• {fed["name"]}</b>\n'
        if "-id" in message.flags:
            output += f'  <code>{fed["_id"]}</code>\n'
        total += 1
    if not total:
        await message.reply("You don't have any Feds Connected.")
        return
    output: str = f"List of <b>{total}</b> Connected Feds:\n\n{output}"
    await message.reply(output, del_in=30, block=True)
