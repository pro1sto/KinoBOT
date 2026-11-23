import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

# --- 1. НАСТРОЙКИ БОТА ---
TOKEN = os.getenv("BOT_TOKEN")

# Список из 3 каналов: ("Текст на кнопке", "Ссылка для перехода", "ID или @username")
CHANNELS = [
    ("📢 Канал 1", "https://t.me/+ifqHCgOXu3UzYzhi", "-1004331132151"),
    ("📢 Канал 2", "https://t.me/+hLg8H8YxhrdlYWFi", "-1002447977734"), # Для закрытых каналов нужен ID
]

# Ссылка, которую получит пользователь после подписки
MOVIE_CHANNEL_LINK = "t.me/KINO_HAP5"
# -------------------------

# Включаем запись логов в консоль, чтобы сразу видеть любые ошибки
logging.basicConfig(level=logging.INFO)

# Инициализируем самого бота и диспетчер (мозг бота, который распределяет команды)
bot = Bot(token=TOKEN)
dp = Dispatcher()


# --- 2. СОЗДАНИЕ КНОПОК ---
def get_sub_keyboard() -> InlineKeyboardMarkup:
    # Создаем список кнопок со ссылками на каналы
    buttons = [
        [InlineKeyboardButton(text=name, url=url)] for name, url, _ in CHANNELS
    ]
    # Добавляем в самый низ кнопку проверки. callback_data — это скрытый сигнал для бота
    buttons.append([InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- 3. ПРОВЕРКА ПОДПИСКИ ---
async def is_subscribed(user_id: int) -> bool:
    for _, _, chat_id in CHANNELS:
        try:
            # Спрашиваем у Telegram статус пользователя в конкретном канале
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            
            # Если статус 'left' (вышел) или 'kicked' (забанен) — значит не подписан
            if member.status in ["left", "kicked"]:
                return False
                
        except TelegramRetryAfter as e:
            # Защита от лагов: если Telegram просит подождать из-за частых запросов, бот ждет
            await asyncio.sleep(e.retry_after)
            return False
        except Exception as e:
            # Если бота забыли сделать админом в канале или неверный ID — пишем ошибку в консоль
            logging.error(f"Ошибка при проверке канала {chat_id}: {e}")
            return False
            
    # Если цикл прошел все 3 канала и не нашел отписок — возвращаем True (подписан)
    return True


# --- 4. ОБРАБОТКА КОМАНДЫ /start ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    # Сразу проверяем, вдруг человек уже подписан на все каналы
    if await is_subscribed(message.from_user.id):
        await message.answer(
            f"\nВот твоя ссылка на канал с фильмами: {MOVIE_CHANNEL_LINK}"
        )
    else:
        await message.answer(
            "🎬 Чтобы получить ссылку на канал с фильмами, подпишись на канала и нажми кнопку проверки:",
            reply_markup=get_sub_keyboard()
        )


# --- 5. ОБРАБОТКА НАЖАТИЯ НА КНОПКУ ПРОВЕРКИ ---
@dp.callback_query(F.data == "check_sub")
async def check_callback(callback: types.CallbackQuery):
    # Проверяем подписку заново
    if await is_subscribed(callback.from_user.id):
        try:
            # Меняем старое сообщение с кнопками на сообщение со ссылкой (чтобы не засорять чат)
            await callback.message.edit_text(
                f"\nВот твоя ссылка на канал с фильмами: {MOVIE_CHANNEL_LINK}"
            )
        except TelegramBadRequest:
            # Защита от ошибки, если пользователь дважды быстро нажал на кнопку
            pass
    else:
        # Показываем всплывающее окно (alert) прямо поверх экрана, если подписался не на всё
        await callback.answer("❌ Вы подписались не на все каналы! Проверьте еще раз.", show_alert=True)


# --- 6. ЗАПУСК БОТА ---
async def main():
    # Удаляем старые сообщения, которые прислали боту, пока он был выключен (чтобы не лагал на старте)
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем бесконечный цикл получения новых сообщений
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")
