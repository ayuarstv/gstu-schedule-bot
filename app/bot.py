import asyncio
import os
import re
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
from os import getenv
from groupes import groups
from loguru import logger
import hashlib

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineQuery, Update
from aiogram.methods import EditMessageText

from utils import (
    get_inline_keyboard_select, get_days_students_keyboard, get_inline_keyboard_disclaimer,
    handle_group_search, handle_teacher_inline_search,
    handle_teacher_inline_search_names, get_human_readable_schedule, get_human_readable_teacher_schedule,
    get_days_teacher_keyboard
)
from api import fetch_schedule_cached, get_teacher_schedule_cached
from db import db
from cache import cache


load_dotenv()
TOKEN = getenv("BOT_TOKEN")
WEBHOOK_URL = getenv("WEBHOOK_URL")  # например https://gstu-schedule-bot.onrender.com
PORT = int(getenv("PORT", "8080"))

dp = Dispatcher()

logger.add("bot.log", rotation="10 MB", retention="30 days", level="INFO")

user_teacher = {}


# =================== КОМАНДЫ ===================

@dp.message(CommandStart())
async def start(message: Message):
    logger.info(f"User {message.from_user.id} started bot")
    await message.answer(
        text="Привет, сначала прочти дисклеймер. \n\n"
        "Этот бот не является официальным приложением ГГТУ и не связан с университетом. \n\n"
        "Автор не несет ответственности за возможные ошибки в расписании. \n\n"
        "Используя этот бот, вы соглашаетесь с тем, что вся информация предоставляется 'как есть' без каких-либо гарантий. \n\n"
        "Если вы не согласны с этими условиями, пожалуйста, не используйте этот бот.\n\n"
        "После принятия условий вы сможете выбрать свою группу и просматривать расписание, а также расписание преподавателей. \n\n"
        "Так-же данный бот OpenSource и вот ссылка на Github:https://github.com/DonTMover/gstu-schedule-bot",
        reply_markup=get_inline_keyboard_disclaimer()
    )


@dp.message(Command("today"))
async def cmd_today(message: Message):
    await show_schedule_for_date(message, date.today(), "Сегодня")


@dp.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message):
    await show_schedule_for_date(message, date.today() + timedelta(days=1), "Завтра")


@dp.message(Command("week"))
async def cmd_week(message: Message):
    await show_schedule_week(message)


@dp.message(Command("next"))
async def cmd_next(message: Message):
    user_group = await db.get_group(message.from_user.id)
    if not user_group:
        await message.answer("Сначала выберите группу через /start", reply_markup=get_inline_keyboard_select())
        return
    try:
        raw = await fetch_schedule_cached(user_group)
        schedule = get_human_readable_schedule(raw)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("📅 Расписание временно недоступно.")
        return

    now = datetime.now()
    today = date.today()
    days_map = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
    ru_day = days_map[today.weekday()]
    lessons_today = schedule.get(ru_day, [])
    next_lesson = None
    time_left = None

    for lesson in lessons_today:
        start_time = lesson.get('startTime')
        if not start_time:
            continue
        try:
            lesson_time = datetime.strptime(start_time, "%H:%M:%S").time()
        except ValueError:
            try:
                lesson_time = datetime.strptime(start_time, "%H:%M").time()
            except ValueError:
                continue
        lesson_dt = datetime.combine(today, lesson_time)
        if lesson_dt > now:
            next_lesson = lesson
            time_left = lesson_dt - now
            break

    if not next_lesson:
        tomorrow = today + timedelta(days=1)
        ru_tomorrow = days_map[tomorrow.weekday()]
        lessons_tomorrow = schedule.get(ru_tomorrow, [])
        if lessons_tomorrow:
            next_lesson = lessons_tomorrow[0]
            try:
                lesson_time = datetime.strptime(next_lesson.get('startTime', '00:00'), "%H:%M:%S").time()
            except ValueError:
                lesson_time = datetime.strptime(next_lesson.get('startTime', '00:00'), "%H:%M").time()
            lesson_dt = datetime.combine(tomorrow, lesson_time)
            time_left = lesson_dt - now

    if not next_lesson:
        await message.answer("🎉 Ближайших пар нет! Можно отдыхать.")
        return

    if time_left:
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        time_str = f"{hours} ч {minutes} мин" if hours > 0 else f"{minutes} мин"
    else:
        time_str = "скоро"

    subj = next_lesson.get('subject') or '—'
    short = next_lesson.get('subjectShort') or ''
    room = next_lesson.get('classrooms') or '-'
    teacher = next_lesson.get('teachers') or '-'
    start = next_lesson.get('startTime', '')[:5] or '??:??'
    end = next_lesson.get('endTime', '')[:5] or '??:??'

    text = (
        f"⏭ <b>Следующая пара через {time_str}</b>\n\n"
        f"📚 {subj} ({short})\n"
        f"🕒 {start} – {end}\n"
        f"🏫 {room}\n"
        f"👨‍🏫 {teacher}"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📚 <b>Команды бота:</b>\n\n"
        "/start — Выбрать группу\n"
        "/today — Расписание на сегодня\n"
        "/tomorrow — Расписание на завтра\n"
        "/week — Расписание на неделю\n"
        "/next — Следующая пара\n"
        "/room [номер] — Кто сегодня в аудитории\n"
        "/notify — Включить/выключить уведомления\n"
        "/help — Эта справка\n\n"
        "💡 <b>Совет:</b> Используйте кнопки быстрого доступа или inline-поиск (@bot группа/преподаватель)"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("room"))
async def cmd_room(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("🔍 Укажите номер аудитории:\n<b>/room 305</b>\n<b>/room 4-305</b>", parse_mode="HTML")
        return

    room_query = args[1].strip().lower()
    wait_msg = await message.answer(f"🔍 Ищу пары в аудитории <b>{room_query}</b>...", parse_mode="HTML")

    semaphore = asyncio.Semaphore(5)
    today = date.today()
    days_map = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
    ru_day = days_map[today.weekday()]

    async def check_group(group_name):
        async with semaphore:
            try:
                raw = await fetch_schedule_cached(group_name)
                schedule = get_human_readable_schedule(raw)
                lessons = schedule.get(ru_day, [])
                found = []
                for lesson in lessons:
                    rooms = (lesson.get('classrooms') or '').lower()
                    if room_query in rooms:
                        found.append(lesson)
                if found:
                    return group_name, found
            except Exception as e:
                logger.warning(f"Room search: skip {group_name} ({e})")
            return None

    tasks = [check_group(name) for name in groups.keys()]
    all_results = await asyncio.gather(*tasks)

    parts = [f"🏫 <b>Аудитория {room_query.upper()}</b> — {today.strftime('%d.%m.%Y')} ({ru_day})\n"]
    found_any = False

    for result in all_results:
        if result:
            group_name, lessons = result
            found_any = True
            parts.append(f"\n👥 <b>Группа {group_name}</b>:")
            for lesson in lessons:
                time = f"{lesson.get('startTime','')[:5] or '??:??'}–{lesson.get('endTime','')[:5] or '??:??'}"
                subj = lesson.get('subject') or '—'
                teacher = lesson.get('teachers') or '-'
                parts.append(f"  🕒 {time} — {subj}")
                parts.append(f"     👨‍🏫 {teacher}")

    if not found_any:
        parts.append("\n❌ Сегодня в этой аудитории занятий нет.")

    await wait_msg.edit_text("\n".join(parts), parse_mode="HTML")


@dp.message(Command("notify"))
async def cmd_notify(message: Message):
    current = await db.get_notify(message.from_user.id)
    new_val = not current
    await db.set_notify(message.from_user.id, new_val)
    status = "✅ включены" if new_val else "❌ выключены"
    await message.answer(
        f"🔔 Уведомления {status}.\n\n"
        f"Бот будет писать за 15 минут до каждой пары.",
        parse_mode="HTML"
    )


@dp.message(Command("test_get_id"))
async def schedule_cmd(message: Message):
    await message.answer(f"Ваш ID: {message.from_user.id}")


# =================== УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК (ПОСЛЕДНИЙ!) ===================

@dp.message()
async def handler(message: Message):
    text = message.text.strip()
    logger.info(f"Received message: {text} from user {message.from_user.id}")

    match_group = re.search(r"Вы выбрали группу: (\S+)", text)
    logger.info(f"Regex match for group: {match_group}")
    if match_group:
        group_code = match_group.group(1)
        await db.set_group(message.from_user.id, group_code)
        logger.info(f"Database updated for user {message.from_user.id} with group {group_code}")
        if group_code in groups:
            logger.info(f"User {message.from_user.id} selected valid group {group_code}")
            await message.answer(
                text="Выберите день недели, чтобы увидеть расписание.",
                reply_markup=get_days_students_keyboard()
            )
        return

    match_teacher_schedule = re.search(r"Преподаватель: (.+)$", text)
    if match_teacher_schedule:
        fullname = match_teacher_schedule.group(1)
        logger.info(f"User {message.from_user.id} selected teacher {fullname} to view schedule")
        slug = await db.get_teacher_by_name(fullname)
        if not slug:
            await message.answer("Преподаватель не найден в базе.")
            return
        user_teacher[message.from_user.id] = {"full_name": fullname, "slug": slug}
        if await db.user_exists(message.from_user.id):
            await db.ensure_user(message.from_user.id)
            await message.answer(
                text="Выберите день недели, чтобы увидеть расписание.",
                reply_markup=get_days_teacher_keyboard()
            )
        else:
            await message.answer(
                text="Сначала выберите группу, используя команду /start",
                reply_markup=get_inline_keyboard_select()
            )
        return


# =================== INLINE QUERY ===================

@dp.inline_query()
async def inline_handler(inline_query: InlineQuery):
    query = inline_query.query.strip()
    results = []
    if query.startswith("teacher:"):
        results = await handle_teacher_inline_search(query.replace("teacher:", "").strip())
    elif query.startswith("group:"):
        results = handle_group_search(query.replace("group:", "").strip())
    elif query.startswith("teacher_schedule:"):
        results = await handle_teacher_inline_search_names(query.replace("teacher_schedule:", "").strip())
    await inline_query.answer(results, cache_time=1)


# =================== CALLBACK QUERY ===================

@dp.callback_query(lambda c: c.data == "search")
async def process_search(callback_query):
    await callback_query.message.answer("Please enter the group code (e.g., АП-11):")
    await callback_query.answer()


@dp.callback_query(lambda c: c.data == "disclaimer:accept")
async def process_disclaimer(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        text="Спасибо за принятие условий. Теперь вы можете выбрать группу.",
        reply_markup=get_inline_keyboard_select()
    )
    await callback_query.answer("Вы приняли условия.")


@dp.callback_query(lambda c: c.data == "comeback")
async def comeback(callback: CallbackQuery):
    await callback.message.edit_text(
        text="Выберите группу снова или перейдите в другой раздел.",
        reply_markup=get_inline_keyboard_select()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("teacher_day:"))
async def teacher_day_schedule(callback: CallbackQuery):
    code = callback.data.split(":")[1]
    days_map = {
        "MONDAY": "Понедельник", "TUESDAY": "Вторник", "WEDNESDAY": "Среда",
        "THURSDAY": "Четверг", "FRIDAY": "Пятница", "SATURDAY": "Суббота",
    }
    day_name = days_map.get(code, code)

    teacher_info = user_teacher.get(callback.from_user.id)
    if not teacher_info:
        await callback.message.edit_text("Сначала выберите преподавателя.", reply_markup=get_inline_keyboard_select())
        await callback.answer()
        return

    teacher_slug = teacher_info.get("slug")
    teacher_fullname = teacher_info.get("full_name")

    try:
        data = await get_teacher_schedule_cached(teacher_slug)
        schedule = get_human_readable_teacher_schedule(data)
        lessons = schedule.get(day_name, [])
    except Exception as e:
        logger.error(f"Error fetching schedule for {teacher_fullname}: {e}")
        await callback.message.edit_text("📅 Расписание пока недоступно.")
        await callback.answer()
        return

    def t(v):
        if not v:
            return "-"
        return v[:5]

    if lessons:
        day_date_iso = lessons[0].get("date")
        week_type = lessons[0].get("weekType") or "-"
    else:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        shift = ["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"].index(code)
        day_date_iso = (monday + timedelta(days=shift)).isoformat()
        week_type = "EVEN" if today.isocalendar().week % 2 == 0 else "ODD"

    try:
        day_date_str = datetime.fromisoformat(day_date_iso).strftime("%d.%m.%Y")
    except Exception:
        day_date_str = day_date_iso

    if not lessons:
        text = f"📅 {day_name}, {day_date_str}  •  Неделя: <b>{week_type}</b>\n\nЗанятий нет 🎉"
    else:
        parts = [f"📅 {day_name}, {day_date_str}  •  Неделя: <b>{week_type}</b>\n"]
        for lesson in lessons:
            parts.append(
                f"<b>{lesson.get('lessonNumber')}. {lesson.get('subject') or '—'}</b>"
                f" ({lesson.get('subjectShort') or ''})\n"
                f"🕒 {t(lesson.get('startTime'))} – {t(lesson.get('endTime'))}\n"
                f"👥 Группы: {lesson.get('groups') or '-'}\n"
                f"🏫 Кабинет: {lesson.get('classrooms') or '-'}\n"
            )
        text = "\n".join(parts)

    await callback.message.edit_text(text, reply_markup=get_days_teacher_keyboard(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("day:"))
async def day_schedule(callback: CallbackQuery):
    code = callback.data.split(":")[1]
    today = date.today()

    if code == "TODAY":
        target_date = today
        day_name = "Сегодня"
    elif code == "TOMORROW":
        target_date = today + timedelta(days=1)
        day_name = "Завтра"
    elif code == "WEEK":
        target_date = None
        day_name = "WEEK"
    else:
        days_map = {
            "MONDAY": "Понедельник", "TUESDAY": "Вторник", "WEDNESDAY": "Среда",
            "THURSDAY": "Четверг", "FRIDAY": "Пятница", "SATURDAY": "Суббота", "SUNDAY": "Воскресенье"
        }
        target_date = today - timedelta(days=today.weekday()) + timedelta(
            days=["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"].index(code)
        )
        day_name = days_map.get(code, code)

    try:
        user_group = await db.get_group(callback.from_user.id)
        if not user_group:
            await callback.message.edit_text("Сначала выберите группу, используя команду /start", reply_markup=get_inline_keyboard_select())
            await callback.answer()
            return
    except Exception as e:
        logger.error(f"Error fetching group: {e}")
        await callback.message.edit_text("Ошибка. Попробуйте /start")
        await callback.answer()
        return

    try:
        raw = await fetch_schedule_cached(user_group)
        schedule = get_human_readable_schedule(raw)
    except Exception as e:
        logger.error(f"Error fetching schedule: {e}")
        await callback.message.edit_text("📅 Расписание временно недоступно.")
        await callback.answer()
        return

    if code == "WEEK":
        week_type = "EVEN" if today.isocalendar().week % 2 == 0 else "ODD"
        parts = [f"📋 Расписание на неделю • {week_type}\n"]
        days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
        for d in days_order:
            lessons = schedule.get(d, [])
            parts.append(f"\n📅 {d}")
            if not lessons:
                parts.append("   Занятий нет 🎉")
            else:
                for lesson in lessons:
                    subj = lesson.get('subject') or '—'
                    time = f"{lesson.get('startTime','')[:5] or '??:??'}–{lesson.get('endTime','')[:5] or '??:??'}"
                    teacher = lesson.get('teachers') or '-'
                    room = lesson.get('classrooms') or '-'
                    num = lesson.get('lessonNumber', '-')
                    parts.append(f"   {num}. {subj}\n   🕒 {time} | 🏫 {room} | 👨‍🏫 {teacher}")
        text = "\n".join(parts)
        await callback.message.edit_text(text, reply_markup=get_days_students_keyboard(), parse_mode="HTML")
        await callback.answer()
        return

    days_map_ru = {
        "MONDAY": "Понедельник", "TUESDAY": "Вторник", "WEDNESDAY": "Среда",
        "THURSDAY": "Четверг", "FRIDAY": "Пятница", "SATURDAY": "Суббота", "SUNDAY": "Воскресенье"
    }
    if code in days_map_ru:
        ru_day = days_map_ru[code]
    else:
        ru_day = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"][target_date.weekday()]

    lessons = schedule.get(ru_day, [])
    week_type = "EVEN" if target_date.isocalendar().week % 2 == 0 else "ODD"
    date_str = target_date.strftime("%d.%m.%Y")

    if not lessons:
        text = f"📅 {ru_day}, {date_str} • Неделя: <b>{week_type}</b>\n\nЗанятий нет 🎉"
    else:
        parts = [f"📅 {ru_day}, {date_str} • Неделя: <b>{week_type}</b>\n"]
        for lesson in lessons:
            subj = lesson.get('subject') or '—'
            short = lesson.get('subjectShort') or ''
            time = f"{lesson.get('startTime','')[:5] or '??:??'}–{lesson.get('endTime','')[:5] or '??:??'}"
            teacher = lesson.get('teachers') or '-'
            room = lesson.get('classrooms') or '-'
            groups_list = lesson.get('groups') or '-'
            num = lesson.get('lessonNumber', '-')
            parts.append(
                f"<b>{num}. {subj}</b> ({short})\n"
                f"🕒 {time}\n"
                f"👨‍🏫 {teacher}\n"
                f"🏫 {room}\n"
                f"👥 {groups_list}\n"
            )
        text = "\n".join(parts)

    await callback.message.edit_text(text, reply_markup=get_days_students_keyboard(), parse_mode="HTML")
    await callback.answer()


# =================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===================

async def show_schedule_for_date(message: Message, target_date: date, label: str):
    user_group = await db.get_group(message.from_user.id)
    if not user_group:
        await message.answer("Сначала выберите группу через /start", reply_markup=get_inline_keyboard_select())
        return
    try:
        raw = await fetch_schedule_cached(user_group)
        schedule = get_human_readable_schedule(raw)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("📅 Расписание временно недоступно.")
        return

    days_map = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
    ru_day = days_map[target_date.weekday()]
    lessons = schedule.get(ru_day, [])
    week_type = "EVEN" if target_date.isocalendar().week % 2 == 0 else "ODD"
    date_str = target_date.strftime("%d.%m.%Y")

    if not lessons:
        text = f"📅 {label}: {ru_day}, {date_str} • Неделя: <b>{week_type}</b>\n\nЗанятий нет 🎉"
    else:
        parts = [f"📅 {label}: {ru_day}, {date_str} • Неделя: <b>{week_type}</b>\n"]
        for lesson in lessons:
            subj = lesson.get('subject') or '—'
            short = lesson.get('subjectShort') or ''
            time = f"{lesson.get('startTime','')[:5] or '??:??'}–{lesson.get('endTime','')[:5] or '??:??'}"
            teacher = lesson.get('teachers') or '-'
            room = lesson.get('classrooms') or '-'
            num = lesson.get('lessonNumber', '-')
            parts.append(f"<b>{num}. {subj}</b> ({short})\n🕒 {time}\n👨‍🏫 {teacher}\n🏫 {room}\n")
        text = "\n".join(parts)
    await message.answer(text, parse_mode="HTML")


async def show_schedule_week(message: Message):
    user_group = await db.get_group(message.from_user.id)
    if not user_group:
        await message.answer("Сначала выберите группу через /start", reply_markup=get_inline_keyboard_select())
        return
    try:
        raw = await fetch_schedule_cached(user_group)
        schedule = get_human_readable_schedule(raw)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("📅 Расписание временно недоступно.")
        return

    today = date.today()
    week_type = "EVEN" if today.isocalendar().week % 2 == 0 else "ODD"
    parts = [f"📋 Расписание на неделю • <b>{week_type}</b>\n"]
    days_order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    for d in days_order:
        lessons = schedule.get(d, [])
        parts.append(f"\n📅 <b>{d}</b>")
        if not lessons:
            parts.append("   Занятий нет 🎉")
        else:
            for lesson in lessons:
                subj = lesson.get('subject') or '—'
                time = f"{lesson.get('startTime','')[:5] or '??:??'}–{lesson.get('endTime','')[:5] or '??:??'}"
                room = lesson.get('classrooms') or '-'
                num = lesson.get('lessonNumber', '-')
                parts.append(f"   {num}. {subj} ({time}, {room})")
    await message.answer("\n".join(parts), parse_mode="HTML")


async def notification_loop(bot: Bot):
    notified_today = set()
    last_date = date.today()
    while True:
        await asyncio.sleep(60)
        today = date.today()
        if today != last_date:
            notified_today.clear()
            last_date = today
        now = datetime.now()
        users = await db.all_users()
        for user_id_str, group in users.items():
            user_id = int(user_id_str)
            if not await db.get_notify(user_id) or not group:
                continue
            try:
                raw = await fetch_schedule_cached(group)
                schedule = get_human_readable_schedule(raw)
                ru_day = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"][today.weekday()]
                lessons = schedule.get(ru_day, [])
                for lesson in lessons:
                    start_time = lesson.get('startTime')
                    if not start_time:
                        continue
                    try:
                        lesson_time = datetime.strptime(start_time, "%H:%M:%S").time()
                    except ValueError:
                        try:
                            lesson_time = datetime.strptime(start_time, "%H:%M").time()
                        except ValueError:
                            continue
                    lesson_dt = datetime.combine(today, lesson_time)
                    diff = (lesson_dt - now).total_seconds()
                    if 870 <= diff <= 930:
                        key = (user_id, lesson.get('lessonNumber'))
                        if key in notified_today:
                            continue
                        subj = lesson.get('subject') or '—'
                        room = lesson.get('classrooms') or '-'
                        time_str = start_time[:5]
                        text = f"⏰ Через 15 минут пара!\n\n📚 {subj}\n🕒 {time_str}\n🏫 {room}"
                        try:
                            await bot.send_message(user_id, text, parse_mode="HTML")
                            notified_today.add(key)
                            logger.info(f"Notification sent to {user_id}: {subj} at {time_str}")
                        except Exception as e:
                            logger.error(f"Notify error for {user_id}: {e}")
            except Exception as e:
                logger.error(f"Notification loop error for {user_id}: {e}")


# =================== WEBHOOK / POLLING ===================

async def on_startup(bot: Bot):
    if WEBHOOK_URL:
        await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
        logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")


async def on_shutdown(bot: Bot):
    if WEBHOOK_URL:
        await bot.delete_webhook()
        logger.info("Webhook deleted")


async def webhook_handler(request: web.Request):
    """Обработчик входящих webhook-запросов от Telegram."""
    bot: Bot = request.app["bot"]
    json_data = await request.json()
    update = Update(**json_data)
    await dp.feed_update(bot, update)
    return web.Response()


async def healthcheck(request: web.Request):
    """Проверка жизни сервера (Render использует для мониторинга)."""
    return web.Response(text="✅ Bot is running!")


async def main():
    logger.info("Bot is starting...")
    bot = Bot(token=TOKEN, properties=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await db.init()
    await cache.init()

    # Запускаем фоновые уведомления
    asyncio.create_task(notification_loop(bot))

    if WEBHOOK_URL:
        # ===== WEBHOOK MODE (Render) =====
        app = web.Application()
        app["bot"] = bot
        app.router.add_post("/webhook", webhook_handler)
        app.router.add_get("/", healthcheck)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)

        await on_startup(bot)
        await site.start()
        logger.info(f"🌐 Server started on port {PORT} in WEBHOOK mode")

        # Держим процесс живым
        while True:
            await asyncio.sleep(3600)
    else:
        # ===== POLLING MODE (локально) =====
        logger.info("🔄 Starting in POLLING mode (local)")
        await dp.start_polling(bot)


def run():
    logger.info("Starting bot...")
    load_dotenv()
    asyncio.run(main())


if __name__ == "__main__":
    run()