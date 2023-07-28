# Kanged From @TroJanZheX
# REDIRECT added https://github.com/Joelkb
import asyncio
import re
import ast
import math
import random
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, AUTH_CHANNEL, FILE_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, NOR_IMG, AUTH_GROUPS, P_TTI_SHOW_OFF, IMDB, \
    SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE, SPELL_IMG, MSG_ALRT, FILE_FORWARD, MAIN_CHANNEL, LOG_CHANNEL, PICS
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results, get_bad_files
from database.filters_mdb import (
    del_all,
    find_filter,
    get_filters,
)
from database.gfilters_mdb import (
    find_gfilter,
    get_gfilters,
)
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}
SPELL_CHECK = {}
FILTER_MODE = {}

@Client.on_message(filters.command('autofilter'))
async def fil_mod(client, message): 
      mode_on = ["yes", "on", "true"]
      mode_of = ["no", "off", "false"]

      try: 
         args = message.text.split(None, 1)[1].lower() 
      except: 
         return await message.reply("**ð™¸ð™½ð™²ð™¾ð™¼ð™¿ð™´ðšƒð™´ð™½ðšƒ ð™²ð™¾ð™¼ð™¼ð™°ð™³...**")
      
      m = await message.reply("**ðš‚ð™´ðšƒðšƒð™¸ð™½ð™¶.../**")

      if args in mode_on:
          FILTER_MODE[str(message.chat.id)] = "True" 
          await m.edit("**ð™°ðš„ðšƒð™¾ð™µð™¸ð™»ðšƒð™´ðš ð™´ð™½ð™°ð™±ð™»ð™´ð™³**")
      
      elif args in mode_of:
          FILTER_MODE[str(message.chat.id)] = "False"
          await m.edit("**ð™°ðš„ðšƒð™¾ð™µð™¸ð™»ðšƒð™´ðš ð™³ð™¸ðš‚ð™°ð™±ð™»ð™´ð™³**")
      else:
          await m.edit("ðš„ðš‚ð™´ :- /autofilter on ð™¾ðš /autofilter off")

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_text(bot, message):
    content = message.text
    user = message.from_user.first_name
    user_id = message.from_user.id
    if content.startswith("/") or content.startswith("#"): return  # ignore commands and hashtags
    await message.reply_text("<b>Your message has been sent to my moderators !</b>")
    await bot.send_message(
        chat_id=LOG_CHANNEL,
        text=f"<b>#PM_MSG\n\nName : {user}\n\nID : {user_id}\n\nMessage : {content}</b>"
    )

@Client.on_message((filters.group | filters.private) & filters.text & filters.incoming)
async def give_filter(client,message):
    await global_filters(client, message)
    group_id = message.chat.id
    name = message.text

    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await message.reply_text(reply_text, disable_web_page_preview=True)
                        else:
                            button = eval(btn)
                            await message.reply_text(
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button)
                            )
                    elif btn == "[]":
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or ""
                        )
                    else:
                        button = eval(btn) 
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button)
                        )
                except Exception as e:
                    print(e)
                break 

    else:
        if FILTER_MODE.get(str(message.chat.id)) == "False":
            return
        else:
            await auto_filter(client, message)


@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name),show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    settings = await get_settings(query.message.chat.id)
    if settings['button']:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"ðŸ“‚ [{get_size(file.file_size)}] {file.file_name}", callback_data=f'files#{file.file_id}'
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}", callback_data=f'files#{file.file_id}'
                ),
                InlineKeyboardButton(
                    text=f"ðŸ“‚ {get_size(file.file_size)}",
                    callback_data=f'files_#{file.file_id}',
                ),
            ]
            for file in files
        ]
    btn.insert(0, 
        [
            InlineKeyboardButton(f' â™€ï¸ {search} â™€ï¸ ', 'qinfo')
        ]
    )
    btn.insert(1, 
         [
             InlineKeyboardButton(f'ðŸ“® ÉªÉ´êœ°á´', 'reqinfo'),
             InlineKeyboardButton(f'ðŸ“Ÿ á´á´á´ Éªá´‡', 'minfo'),
             InlineKeyboardButton(f'ðŸ”¶ sá´‡Ê€Éªá´‡s', 'sinfo'),
             InlineKeyboardButton(f'ðŸŽ á´›Éªá´˜s', 'tinfo')
         ]
    )

    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("âª» ð“‘ð“ªð“¬ð“´", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"Ïêª–á§ê«€ {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}",
                                  callback_data="pages")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
             InlineKeyboardButton("ð“ð“®ð”ð“½ âª¼", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("âª» ð“‘ð“ªð“¬ð“´", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f" {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
                InlineKeyboardButton("ð“ð“®ð”ð“½ âª¼", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass
    await query.answer()

#SpellCheck bug fixing
@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    movies = SPELL_CHECK.get(query.message.reply_to_message.id)
    if not movies:
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name),show_alert=True)
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    movie = movies[(int(movie_))]
    await query.answer(script.TOP_ALRT_MSG)
    k = await manual_filters(bot, query.message, text=movie)
    if k == False:
        files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
        if files:
            k = (movie, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            reqstr1 = query.from_user.id if query.from_user else 0
            reqstr = await bot.get_users(reqstr1)
            await bot.send_message(chat_id=LOG_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, movie)))
            k = await query.message.edit(script.MVE_NT_FND)
            await asyncio.sleep(10)
            await k.delete()


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!!", quote=True)
                    return await query.answer(MSG_ALRT)
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True
                )
                return await query.answer(MSG_ALRT)

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer(MSG_ALRT)

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that!", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer(script.ALRT_TXT.format(query.from_user.first_name),show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return await query.answer(MSG_ALRT)
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text('Some error occurred!!', parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer(MSG_ALRT)
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer(MSG_ALRT)
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer(MSG_ALRT)
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer(MSG_ALRT)
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    elif "gfilteralert" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_gfilter('gfilters', keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    if query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        clicked = query.from_user.id #fetching the ID of the user who clicked the button
        try:
            typed = query.message.reply_to_message.from_user.id #fetching user ID of the user who sent the movie request
        except:
            typed = clicked #if failed, uses the clicked user's ID as requested user ID
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if clicked == typed: #checking whether clicked user is the requested user or not
                if AUTH_CHANNEL and not await is_subscribed(client, query):
                    await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                    return
                elif settings['botpm']:
                    await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                    await query.answer('ð˜¾ð™ð™šð™˜ð™  ð™‹ð™ˆ, ð™„ ð™ð™–ð™«ð™š ð™¨ð™šð™£ð™© ð™›ð™žð™¡ð™šð™¨ ð™žð™£ ð™¥ð™¢\n@á´„á´„á´á´_á´›á´‡á´€á´', show_alert=True)
                    return
                else:
                    file_send=await client.send_cached_media(
                        chat_id=FILE_CHANNEL,
                        file_id=file_id,
                        caption=script.CHANNEL_CAP.format(query.from_user.mention, title, query.message.chat.title),
                        protect_content=True if ident == "filep" else False,
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton("ðŸ”¥ á´„Êœá´€É´É´á´‡ÊŸ ðŸ”¥", url=(MAIN_CHANNEL))
                                ]
                            ]
                        )
                    )
                    Joel_tgx = await query.message.reply_text(
                        script.FILE_MSG.format(query.from_user.mention, title, size),
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(
                            [
                             [
                              InlineKeyboardButton('ðŸ“¥ ð–£ð—ˆð—ð—‡ð—…ð—ˆð–ºð–½ ð–«ð—‚ð—‡ð—„ ðŸ“¥ ', url = file_send.link)
                           ],[
                              InlineKeyboardButton("âš ï¸ ð–¢ð–ºð—‡'ð— ð– ð–¼ð–¼ð–¾ð—Œð—Œ â“ ð–¢ð—…ð—‚ð–¼ð—„ ð–§ð–¾ð—‹ð–¾ âš ï¸", url=(FILE_FORWARD))
                             ]
                            ]
                        )
                    )
                    if settings['auto_delete']:
                        await asyncio.sleep(600)
                        await Joel_tgx.delete()
                        await file_send.delete()
            else: #if not, bot shows alert msg
                await query.answer(f"Hey {query.from_user.first_name}, This is not your movie request, Request Your's !")
        except UserIsBlocked:
            await query.answer('ð”ð§ð›ð¥ð¨ðœð¤ ð­ð¡ðž ð›ð¨ð­ ð¦ðšð¡ð§ !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
    elif query.data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("ð‘° ð‘³ð’Šð’Œð’† ð’€ð’ð’–ð’“ ð‘ºð’Žð’‚ð’“ð’•ð’ð’†ð’”ð’”, ð‘©ð’–ð’• ð‘«ð’ð’'ð’• ð‘©ð’† ð‘¶ð’—ð’†ð’“ð’”ð’Žð’‚ð’“ð’• ðŸ˜’\n@All_Links2022", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
        if f_caption is None:
            f_caption = f"{title}"
        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False
        )
    elif query.data == "predvd":
        k = await client.send_message(chat_id=query.message.chat.id, text="<b>Deleting PreDVDs... Please wait...</b>")
        files, next_offset, total = await get_bad_files(
                                                  'predvd',
                                                  offset=0)
        deleted = 0
        for file in files:
            file_ids = file.file_id
            result = await Media.collection.delete_one({
                '_id': file_ids,
            })
            if result.deleted_count:
                logger.info('PreDVD File Found ! Successfully deleted from database.')
            deleted+=1
        deleted = str(deleted)
        await k.edit_text(text=f"<b>Successfully deleted {deleted} PreDVD files.</b>")

    elif query.data == "camrip":
        k = await client.send_message(chat_id=query.message.chat.id, text="<b>Deleting CamRips... Please wait...</b>")
        files, next_offset, total = await get_bad_files(
                                                  'camrip',
                                                  offset=0)
        deleted = 0
        for file in files:
            file_ids = file.file_id
            result = await Media.collection.delete_one({
                '_id': file_ids,
            })
            if result.deleted_count:
                logger.info('CamRip File Found ! Successfully deleted from database.')
            deleted+=1
        deleted = str(deleted)
        await k.edit_text(text=f"<b>Successfully deleted {deleted} CamRip files.</b>")

    elif query.data == "pages":
        await query.answer()

    elif query.data == "reqinfo":
        await query.answer("âš  ÉªÉ´êœ°á´Ê€á´á´€á´›Éªá´É´ âš \n\ná´€êœ°á´›á´‡Ê€ 10 á´ÉªÉ´á´œá´›á´‡êœ± á´›ÊœÉªêœ± á´á´‡êœ±êœ±á´€É¢á´‡ á´¡ÉªÊŸÊŸ Ê™á´‡ á´€á´œá´›á´á´á´€á´›Éªá´„á´€ÊŸÊŸÊ á´…á´‡ÊŸá´‡á´›á´‡á´…\n\nÉªêœ° Êá´á´œ á´…á´ É´á´á´› êœ±á´‡á´‡ á´›Êœá´‡ Ê€á´‡Ç«á´œá´‡sá´›á´‡á´… á´á´á´ Éªá´‡ / sá´‡Ê€Éªá´‡s êœ°ÉªÊŸá´‡, ÊŸá´á´á´‹ á´€á´› á´›Êœá´‡ É´á´‡xá´› á´˜á´€É¢á´‡\n\nâ£ á´˜á´á´¡á´‡Ê€á´‡á´… Ê™Ê All_Links2022", show_alert=True)

    elif query.data == "minfo":
        await query.answer("â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯\ná´á´á´ Éªá´‡ Ê€á´‡Ç«á´œá´‡êœ±á´› êœ°á´Ê€á´á´€á´›\nâ‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯\n\nÉ¢á´ á´›á´ É¢á´á´É¢ÊŸá´‡ âž  á´›Êá´˜á´‡ á´á´á´ Éªá´‡ É´á´€á´á´‡ âž  á´„á´á´˜Ê á´„á´Ê€Ê€á´‡á´„á´› É´á´€á´á´‡ âž  á´˜á´€êœ±á´›á´‡ á´›ÊœÉªêœ± É¢Ê€á´á´œá´˜\n\ná´‡xá´€á´á´˜ÊŸá´‡ : á´€á´ á´€á´›á´€Ê€: á´›Êœá´‡ á´¡á´€Ê á´Ò“ á´¡á´€á´›á´‡Ê€\n\nðŸš¯ á´…á´É´á´› á´œêœ±á´‡ âž  ':(!,./)\n\nÂ©ï¸ CCHDMovie", show_alert=True)

    elif query.data == "sinfo":
        await query.answer("â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯\nêœ±á´‡Ê€Éªá´‡êœ± Ê€á´‡Ç«á´œá´‡êœ±á´› êœ°á´Ê€á´á´€á´›\nâ‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯â‹¯\n\nÉ¢á´ á´›á´ É¢á´á´É¢ÊŸá´‡ âž  á´›Êá´˜á´‡ á´á´á´ Éªá´‡ É´á´€á´á´‡ âž  á´„á´á´˜Ê á´„á´Ê€Ê€á´‡á´„á´› É´á´€á´á´‡ âž  á´˜á´€êœ±á´›á´‡ á´›ÊœÉªêœ± É¢Ê€á´á´œá´˜\n\ná´‡xá´€á´á´˜ÊŸá´‡ : á´á´É´á´‡Ê Êœá´‡Éªsá´› S01E01\n\nðŸš¯ á´…á´É´á´› á´œêœ±á´‡ âž  ':(!,./)\n\nÂ©ï¸ CCHDMovie", show_alert=True)      

    elif query.data == "tinfo":
        await query.answer("â–£ á´›Éªá´˜s â–£\n\nâ˜… á´›Êá´˜á´‡ á´„á´Ê€Ê€á´‡á´„á´› sá´˜á´‡ÊŸÊŸÉªÉ´É¢ (É¢á´á´É¢ÊŸá´‡)\n\nâ˜… ÉªÒ“ Êá´á´œ É´á´á´› É¢á´‡á´› Êá´á´œÊ€ Ò“ÉªÊŸá´‡ ÉªÉ´ á´›Êœá´‡ Ê™á´œá´›á´›á´É´ á´›Êœá´‡É´ á´›Êœá´‡ É´á´‡xá´› sá´›á´‡á´˜ Éªs á´„ÊŸÉªá´„á´‹ É´á´‡xá´› Ê™á´œá´›á´›á´É´.\n\nâ˜… á´„á´É´á´›ÉªÉ´á´œá´‡ á´›ÊœÉªs á´á´‡á´›Êœá´á´… á´›á´ É¢á´‡á´›á´›ÉªÉ´É¢ Êá´á´œ Ò“ÉªÊŸá´‡\n\nâ£ á´˜á´á´¡á´‡Ê€á´‡á´… Ê™Ê CCHDMovie", show_alert=True)

    elif query.data == "surprise":
        btn = [[
            InlineKeyboardButton('sá´œÊ€á´˜Ê€Éªsá´‡', callback_data='start')
        ]]
        reply_markup=InlineKeyboardMarkup(btn)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.SUR_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('Ã— ð—”ð——ð—— ð— ð—˜ ð—§ð—¢ ð—¬ð—¢ð—¨ð—¥ ð—šð—¥ð—¢ð—¨ð—£ð—¦ Ã—', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ], [
            InlineKeyboardButton('ðŸ” ð—¦ð—˜ð—”ð—¥ð—–ð—›', switch_inline_query_current_chat=''),
            InlineKeyboardButton('ð—¨ð—£ð——ð—”ð—§ð—˜ð—¦', url='https://t.me/CCHDMovie')
        ], [
            InlineKeyboardButton('ð—›ð—˜ð—Ÿð—£', callback_data='help'),
            InlineKeyboardButton('ð—”ð—•ð—¢ð—¨ð—§', callback_data='about')
         ],[
            InlineKeyboardButton('Ê™á´€á´„á´‹ á´›á´ sá´›á´€Ê€á´›', callback_data='surprise')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        await query.answer(MSG_ALRT)
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('á´á´€É´á´œá´€ÊŸ', callback_data='manuelfilter'),
            InlineKeyboardButton('á´€á´œá´›á´', callback_data='autofilter'),
            InlineKeyboardButton('á´„á´É´É´á´‡á´„á´›', callback_data='coct')
        ], [
            InlineKeyboardButton('á´‡xá´›Ê€á´€', callback_data='extra'),
            InlineKeyboardButton('sá´É´É¢', callback_data='song'),
            InlineKeyboardButton('á´›á´›s', callback_data='tts')
        ], [
            InlineKeyboardButton('á´ Éªá´…á´‡á´', callback_data='video'),
            InlineKeyboardButton('á´›_É¢Ê€á´€á´˜Êœ', callback_data='tele'),
            InlineKeyboardButton('É´á´‡xá´›', callback_data='aswin')    
        ], [
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='start')      
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="â˜… â˜† â˜† â˜† â˜†"
        )
        await query.message.edit_text(
            text="â˜… â˜… â˜† â˜† â˜†"
        )
        await query.message.edit_text(
            text="â˜… â˜… â˜… â˜† â˜†"
        )
        await query.message.edit_text(
            text="â˜… â˜… â˜… â˜… â˜†"
        )
        await query.message.edit_text(
            text="â˜… â˜… â˜… â˜… â˜…"
        )       
        await query.message.edit_text(                     
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "aswin":
        buttons = [[
             InlineKeyboardButton('á´€á´œá´…_Ê™á´á´á´‹', callback_data='abook'),
             InlineKeyboardButton('á´„á´á´ Éªá´…', callback_data='corona'),
             InlineKeyboardButton('É¢á´€á´á´‡s', callback_data='fun')
         ], [
             InlineKeyboardButton('á´˜ÉªÉ´É¢', callback_data='pings'),
             InlineKeyboardButton('á´Šsá´É´á´‡', callback_data='json'),
             InlineKeyboardButton('sá´›Éªá´„á´‹_Éªá´…', callback_data='sticker')
         ], [
             InlineKeyboardButton('á´¡Êœá´Éªs', callback_data='whois'),
             InlineKeyboardButton('á´œÊ€ÊŸ_sÊœá´Ê€á´›', callback_data='urlshort'),
             InlineKeyboardButton('É´á´‡xá´›', callback_data='aswins')  
        ], [
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help')         
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="â˜… â˜† â˜† â˜† â˜†"
        )
        await query.message.edit_text(
            text="â˜… â˜… â˜† â˜† â˜†"
        )
        await query.message.edit_text(
            text="â˜… â˜… â˜… â˜† â˜†"
        )
        await query.message.edit_text(
            text="â˜… â˜… â˜… â˜… â˜†"
        )
        await query.message.edit_text(
            text="â˜… â˜… â˜… â˜… â˜…"
        )       
        await query.message.edit_text(                     
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "aswins":
        buttons = [[
             InlineKeyboardButton('Ò“á´É´á´›', callback_data='font'),
             InlineKeyboardButton('É¢_á´›Ê€á´€É´s', callback_data='gtrans'),
             InlineKeyboardButton('á´„á´€Ê€Ê™á´É´', callback_data='carb'),
        ],  [
             InlineKeyboardButton('á´„á´á´œÉ´á´›Ê€Ê', callback_data='country'),
             InlineKeyboardButton('á´…á´‡á´˜ÊŸá´Ê', callback_data='deploy'),
             InlineKeyboardButton('Êœá´á´á´‡', callback_data='start')
        ], [
             InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text="â–£ â–¢ â–¢"
        )
        await query.message.edit_text(
            text="â–£ â–£ â–¢"
        )
        await query.message.edit_text(
            text="â–£ â–£ â–£"
        )
        await query.message.edit_text(                     
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('sá´›á´€á´›á´œs', callback_data='stats'),
            InlineKeyboardButton('sá´á´œÊ€á´„á´‡', callback_data='source')
        ], [
            InlineKeyboardButton('Êœá´á´á´‡', callback_data='start'),
            InlineKeyboardButton('á´„ÊŸá´sá´‡', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('Ê€á´‡á´˜á´', url='https://github.com/Devil-Botz/Elsa'),
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.SOURCE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "manuelfilter":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help'),
            InlineKeyboardButton('Ê™á´œá´›á´›á´É´s', callback_data='button')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MANUELFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "button":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='manuelfilter')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.BUTTON_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "autofilter":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.AUTOFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "coct":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CONNECTION_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "extra":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help'),
            InlineKeyboardButton('á´€á´…á´ÉªÉ´', callback_data='admin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.EXTRAMOD_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "admin":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='extra')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ADMIN_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "song":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.SONG_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "video":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.VIDEO_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "tts":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.TTS_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "gtrans":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswins'),
            InlineKeyboardButton('ð™»ð™°ð™½ð™¶ ð™²ð™¾ð™³ð™´ðš‚', url='https://cloud.google.com/translate/docs/languages')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.GTRANS_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "country":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswins'),
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CON_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "tele":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.TELE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "corona":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CORONA_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "abook":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ABOOK_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "deploy":
        buttons = [[
           InlineKeyboardButton('Ê€á´‡á´˜á´', url='https://github.com/Devil-Botz/Elsa'),
           InlineKeyboardButton('á´á´¡É´á´‡Ê€', url='https://t.me/Aswin_pm_Bot')
        ], [
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.DEPLOY_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "sticker":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.STICKER_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "pings":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.PINGS_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "json":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.JSON_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "urlshort":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.URLSHORT_TXT,
            disable_web_page_preview=True,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "whois":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.WHOIS_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "font":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswins')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.FONT_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "carb":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='aswins')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CARB_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "fun":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.FUN_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='start'),
            InlineKeyboardButton('Ê€á´‡Ò“Ê€á´‡sÊœ', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "rfrsh":
        await query.answer("ð™ð™šð™©ð™˜ð™ð™žð™£ð™œ ð™ˆð™¤ð™£ð™œð™¤ð˜¿ð™— ð˜¿ð™–ð™©ð™–ð˜½ð™–ð™¨ð™š")
        buttons = [[
            InlineKeyboardButton('Ê™á´€á´„á´‹', callback_data='start'),
            InlineKeyboardButton('Ê€á´‡Ò“Ê€á´‡sÊœ', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))

        if str(grp_id) != str(grpid):
            await query.message.edit("Your Active Connection Has Been Changed. Go To /settings.")
            return await query.answer(MSG_ALRT)

        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)
        try:
            if settings['auto_delete']:
                settings = await get_settings(grp_id)
        except KeyError:
            await save_group_settings(grp_id, 'auto_delete', True)
            settings = await get_settings(grp_id)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Redirect To', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Bot PM' if settings["botpm"] else 'Channel',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('âœ… Yes' if settings["file_secure"] else 'âŒ No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('âœ… Yes' if settings["imdb"] else 'âŒ No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spell Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('âœ… Yes' if settings["spell_check"] else 'âŒ No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('âœ… Yes' if settings["welcome"] else 'âŒ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Auto Delete',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}'),
                    InlineKeyboardButton('10 Mins' if settings["auto_delete"] else 'OFF',
                                         callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    await query.answer(MSG_ALRT)


async def auto_filter(client, msg, spoll=False):
    reqstr1 = msg.from_user.id if msg.from_user else 0
    reqstr = await client.get_users(reqstr1)
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        if message.text.startswith("/"): return  # ignore commands
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if len(message.text) < 100:
            search = message.text
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            if not files:
                if settings["spell_check"]:
                    return await advantage_spell_chok(client, msg)
                else:
                    await client.send_message(chat_id=LOG_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, search)))
                    return
        else:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    pre = 'filep' if settings['file_secure'] else 'file'
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"ðŸ“‚ [{get_size(file.file_size)}] {file.file_name}", callback_data=f'{pre}#{file.file_id}'
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}",
                    callback_data=f'{pre}#{file.file_id}',
                ),
                InlineKeyboardButton(
                    text=f"ðŸ“‚ {get_size(file.file_size)}",
                    callback_data=f'{pre}#{file.file_id}',
                ),
            ]
            for file in files
        ]
    btn.insert(0, 
        [
            InlineKeyboardButton(f' â™€ï¸ {search} â™€ï¸ ', 'qinfo')
        ]
    )
    btn.insert(1, 
         [
             InlineKeyboardButton(f'ðŸ“® ÉªÉ´êœ°á´', 'reqinfo'),
             InlineKeyboardButton(f'ðŸ“Ÿ á´á´á´ Éªá´‡', 'minfo'),
             InlineKeyboardButton(f'ðŸ”¶ sá´‡Ê€Éªá´‡s', 'sinfo'),
             InlineKeyboardButton(f'ðŸŽ á´›Éªá´˜s', 'tinfo')
         ]
    )

    if offset != "":
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f" 1/{math.ceil(int(total_results) / 10)}", callback_data="pages"),
             InlineKeyboardButton(text="ð“ð“®ð”ð“½ âª¼", callback_data=f"next_{req}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text=" 1/1", callback_data="pages")]
        )
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            **locals()
        )
    else:
        cap = f"<b><i>ð™ƒð™šð™§ð™š ð™žð™¨ ð™¬ð™ð™–ð™© ð™žð™¨ ð™›ð™¤ð™ªð™£ð™™ ð™®ð™¤ð™ªð™§ ð™¦ð™ªð™šð™§ð™®:\n {search}\nðŸ‘¤ð™ð™šð™¦ð™ªð™šð™¨ð™©ð™šð™™ ð˜½ð™® : {message.from_user.mention}\nðŸ‘¥ð™‚ð™§ð™¤ð™ªð™¥ : {message.chat.title}</i></b>"
    if imdb and imdb.get('poster'):
        try:
            pic_fi=await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024],
                                      reply_markup=InlineKeyboardMarkup(btn))
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(300)
                    await pic_fi.delete()
                    await message.delete()
            except KeyError:
                grpid = await active_connection(str(message.from_user.id))
                await save_group_settings(grpid, 'auto_delete', True)
                settings = await get_settings(message.chat.id)
                if settings['auto_delete']:
                    await asyncio.sleep(300)
                    await pic_fi.delete()
                    await message.delete()
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            pic_fil=await message.reply_photo(photo=poster, caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(300)
                    await pic_fil.delete()
                    await message.delete()
            except KeyError:
                grpid = await active_connection(str(message.from_user.id))
                await save_group_settings(grpid, 'auto_delete', True)
                settings = await get_settings(message.chat.id)
                if settings['auto_delete']:
                    await asyncio.sleep(300)
                    await pic_fil.delete()
                    await message.delete()
        except Exception as e:
            logger.exception(e)
            no_pic=await message.reply_photo(photo=NOR_IMG, caption=cap, reply_markup=InlineKeyboardMarkup(btn))
            try:
                if settings['auto_delete']:
                    await asyncio.sleep(300)
                    await no_pic.delete()
                    await message.delete()
            except KeyError:
                grpid = await active_connection(str(message.from_user.id))
                await save_group_settings(grpid, 'auto_delete', True)
                settings = await get_settings(message.chat.id)
                if settings['auto_delete']:
                    await asyncio.sleep(300)
                    await no_pic.delete()
                    await message.delete()
    else:
        no_fil=await message.reply_photo(photo=NOR_IMG, caption=cap, reply_markup=InlineKeyboardMarkup(btn))
        try:
            if settings['auto_delete']:
                await asyncio.sleep(300)
                await no_fil.delete()
                await message.delete()
        except KeyError:
            grpid = await active_connection(str(message.from_user.id))
            await save_group_settings(grpid, 'auto_delete', True)
            settings = await get_settings(message.chat.id)
            if settings['auto_delete']:
                await asyncio.sleep(300)
                await no_fil.delete()
                await message.delete()
    if spoll:
        await msg.message.delete()


async def advantage_spell_chok(client, msg):
    mv_id = msg.id
    mv_rqst = msg.text
    reqstr1 = msg.from_user.id if msg.from_user else 0
    reqstr = await client.get_users(reqstr1)
    settings = await get_settings(msg.chat.id)
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE)  # plis contribute some common words
    RQST = query.strip()
    query = query.strip() + " movie"
    try:
        movies = await get_poster(mv_rqst, bulk=True)
    except Exception as e:
        logger.exception(e)
        await client.send_message(chat_id=LOG_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, mv_rqst)))
        k = await msg.reply(script.I_CUDNT.format(reqstr.mention))
        await asyncio.sleep(8)
        await k.delete()
        return
    movielist = [] #error fixed
    if not movies:
        reqst_gle = mv_rqst.replace(" ", "+")
        button = [[
                   InlineKeyboardButton("Gá´á´É¢ÊŸá´‡", url=f"https://www.google.com/search?q={reqst_gle}")
        ]]
        await client.send_message(chat_id=LOG_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, mv_rqst)))
        k = await msg.reply_photo(
            photo=SPELL_IMG, 
            caption=script.I_CUDNT.format(mv_rqst),
            reply_markup=InlineKeyboardMarkup(button)
        )
        await asyncio.sleep(30)
        await k.delete()
        return
    movielist += [movie.get('title') for movie in movies]
    movielist += [f"{movie.get('title')} {movie.get('year')}" for movie in movies]
    SPELL_CHECK[mv_id] = movielist
    btn = [
        [
            InlineKeyboardButton(
                text=movie_name.strip(),
                callback_data=f"spol#{reqstr1}#{k}",
            )
        ]
        for k, movie_name in enumerate(movielist)
    ]
    btn.append([InlineKeyboardButton(text="Close", callback_data=f'spol#{reqstr1}#close_spellcheck')])
    spell_check_del = await msg.reply_photo(
        photo=(SPELL_IMG),
        caption=(script.CUDNT_FND.format(reqstr.mention)),
        reply_markup=InlineKeyboardMarkup(btn)
        )

    try:
        if settings['auto_delete']:
            await asyncio.sleep(600)
            await spell_check_del.delete()
    except KeyError:
            grpid = await active_connection(str(message.from_user.id))
            await save_group_settings(grpid, 'auto_delete', True)
            settings = await get_settings(message.chat.id)
            if settings['auto_delete']:
                await asyncio.sleep(600)
                await spell_check_del.delete()

async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await client.send_message(group_id, reply_text, disable_web_page_preview=True)
                        else:
                            button = eval(btn)
                            await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                    elif btn == "[]":
                        await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(btn)
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False

async def global_filters(client, message, text=False):
    settings = await get_settings(message.chat.id)
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_gfilters('gfilters')
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_gfilter('gfilters', keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            joelkb = await client.send_message(
                                group_id, 
                                reply_text, 
                                disable_web_page_preview=True,
                                reply_to_message_id=reply_id
                            )
                            
                        else:
                            button = eval(btn)
                            hmm = await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )

                    elif btn == "[]":
                        oto = await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )

                    else:
                        button = eval(btn)
                        dlt = await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )

                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
