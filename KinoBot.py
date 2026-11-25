TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 994444870

# Каналы с обязательной проверкой подписки
CHANNELS = [
    ("📢 Канал 1", "https://t.me/+vkpdBtTaBiViNDEy", "-1004331132151"),
    ("📢 Канал 2", "https://t.me/+hLg8H8YxhrdlYWFi", "-1002447977734"),
]

# Другие боты (без проверки подписки)
REQUIRED_BOTS = [
    ("🤖 Канал 3", "https://t.me/SaveInstTTbot"),
]

MOVIE_CHANNEL_LINK = "https://t.me/+0eyPhEyL5XFjNmZi"
# ---------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


# --- 2. БАЗА ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")


def add_user(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))


def get_all_users() -> list[int]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]


def remove_user(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


# --- 3. КНОПКИ ---
def get_sub_keyboard() -> InlineKeyboardMarkup:
    buttons = []

    # Каналы
    for name, url, _ in CHANNELS:
        buttons.append([
            InlineKeyboardButton(
                text=name,
                url=url
            )
        ])

    # Другие боты (без проверки)
    for name, url in REQUIRED_BOTS:
        buttons.append([
            InlineKeyboardButton(
                text=name,
                url=url
            )
        ])

    # Кнопка проверки
    buttons.append([
        InlineKeyboardButton(
            text="✅ Проверить подписку",
            callback_data="check_sub"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# --- 4. ПРОВЕРКА ПОДПИСКИ ---
async def is_subscribed(user_id: int) -> bool:
    for _, _, chat_id in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            return False
        except Exception as e:
            logging.error(f"Ошибка при проверке канала {chat_id}: {e}")
            return False
    return True

# --- 5. КОМАНДЫ АДМИНИСТРАТОРА ---
@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    users = get_all_users()
    await message.answer(f"📊 Живых пользователей в базе: **{len(users)}**", parse_mode="Markdown")


@dp.message(Command("send"))
async def send_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    text_to_send = message.text.replace("/send", "", 1).strip()
    if not text_to_send:
        await message.answer(
            "❗ Напишите текст рассылки после команды.\nПример:\n`/send Вышел новый фильм! Смотри тут: https://t.me`",
            parse_mode="Markdown"
        )
        return

    users = get_all_users()
    status_msg = await message.answer(f"🚀 Запускаю рассылку по {len(users)} пользователям...")

    success = 0
    removed = 0

    for uid in users:
        try:
            await bot.send_message(chat_id=uid, text=text_to_send)
            success += 1
            await asyncio.sleep(0.05)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=uid, text=text_to_send)
                success += 1
            except Exception:
                pass
        except TelegramForbiddenError:
            remove_user(uid)
            removed += 1
        except Exception:
            pass

    await status_msg.edit_text(
        f"✅ **Рассылка завершена!**\n"
        f"📨 Доставлено: **{success}**\n"
        f"🗑 Очищено заблокировавших: **{removed}**",
        parse_mode="Markdown"
    )


# --- 6. СТАРТ И ПРОВЕРКА ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)

    if await is_subscribed(message.from_user.id):
        await message.answer(f"🎬 Вот твоя ссылка на канал с фильмами: {MOVIE_CHANNEL_LINK}")
    else:
        await message.answer(
            "🎬 Чтобы получить ссылку на канал с фильмами, подпишись на каналы и нажми кнопку проверки:",
            reply_markup=get_sub_keyboard()
        )


@dp.callback_query(F.data == "check_sub")
async def check_callback(callback: types.CallbackQuery):
    add_user(callback.from_user.id)

    if await is_subscribed(callback.from_user.id):
        try:
            await callback.message.edit_text(f"🎬 Вот твоя ссылка на канал с фильмами: {MOVIE_CHANNEL_LINK}")
        except TelegramBadRequest:
            pass
    else:
        await callback.answer("❌ Вы подписались не на все каналы! Проверьте еще раз.", show_alert=True)


# --- 7. ЗАПУСК ---
async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен.")

