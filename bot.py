import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram import F
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ===== НАСТРОЙКИ =====
TOKEN = "8324972961:AAE5pO64tLLcmCP9ABWSqDn7SYrJE_mIKOc"  # Замените на токен вашего бота
WIFE_USER_ID = 974924604  # Замените на Telegram ID жены
REMINDER_DAY = 20  # Число месяца для напоминания
REMINDER_TIME_HOUR = 13  # Час для ежедневных напоминаний
REMINDER_TIME_MINUTE = 0  # Минуты
DATA_FILE = "state.json"  # Файл для хранения состояния

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


# ===== РАБОТА С ФАЙЛОМ СОСТОЯНИЯ =====
def load_state():
    """Загружает состояние из JSON-файла."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    return {"paid_this_month": False, "last_reminded_day": None}


def save_state(state):
    """Сохраняет состояние в JSON-файл."""
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ===== КНОПКА =====
def get_paid_keyboard():
    """Клавиатура с кнопкой 'Оплатила'."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Оплатила")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


# ===== ОТПРАВКА НАПОМИНАНИЯ =====
async def send_reminder():
    """Отправляет сообщение-напоминание с кнопкой."""
    try:
        await bot.send_message(
            WIFE_USER_ID,
            f"💰 Напоминание: сегодня {REMINDER_DAY}-е число! Нужно передать показания и оплатить.",
            reply_markup=get_paid_keyboard()
        )
        print(f"[{datetime.now()}] Напоминание отправлено.")
    except Exception as e:
        print(f"Ошибка при отправке: {e}")


# ===== ПРОВЕРКА ДНЯ И ЗАПУСК НАПОМИНАНИЙ =====
async def check_date_and_remind():
    """Проверяет, наступило ли нужное число, и запускает напоминания."""
    state = load_state()
    today = datetime.now().day
    current_month = datetime.now().month

    # Если сегодня нужное число и ещё не оплачено в этом месяце
    if today == REMINDER_DAY and not state["paid_this_month"]:
        await send_reminder()
        state["last_reminded_day"] = today
        save_state(state)


# ===== ЕЖЕДНЕВНАЯ ЗАДАЧА =====
async def daily_reminder_task():
    """Ежедневная задача: напоминать, если ещё не оплачено и число >= нужного."""
    state = load_state()
    today = datetime.now().day

    # Если не оплачено в этом месяце и сегодня >= дня напоминания
    if not state["paid_this_month"] and today >= REMINDER_DAY:
        await send_reminder()
        state["last_reminded_day"] = today
        save_state(state)


# ===== ОБРАБОТЧИК КНОПКИ "ОПЛАТИЛА" =====
@dp.message(F.text == "✅ Оплатила")
async def handle_paid(message: types.Message):
    """Обрабатывает нажатие кнопки 'Оплатила'."""
    if message.from_user.id != WIFE_USER_ID:
        await message.answer("Это не для вас 😊")
        return

    state = load_state()
    state["paid_this_month"] = True
    save_state(state)

    await message.answer(
        "Спасибо! Напоминания отключены до следующего месяца.",
        reply_markup=ReplyKeyboardRemove()  # Убираем кнопку
    )

    print(f"[{datetime.now()}] Жена подтвердила оплату.")


# ===== СБРОС СТАТУСА В НАЧАЛЕ НОВОГО МЕСЯЦА =====
async def reset_paid_status():
    """Каждое 1-е число сбрасывает флаг оплаты."""
    state = load_state()
    if state["paid_this_month"]:
        state["paid_this_month"] = False
        save_state(state)
        print(f"[{datetime.now()}] Статус оплаты сброшен (новый месяц).")

        # Отправляем уведомление о новом месяце
        try:
            await bot.send_message(
                WIFE_USER_ID,
                f"📅 Наступил новый месяц! {REMINDER_DAY}-го числа я напомню о показаниях снова."
            )
        except Exception as e:
            print(f"Ошибка при отправке уведомления о новом месяце: {e}")


# ===== КОМАНДА СТАРТ =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    if message.from_user.id == WIFE_USER_ID:
        await message.answer(
            f"Привет! Я буду напоминать тебе о передаче показаний {REMINDER_DAY}-го числа каждого месяца.\n"
            f"Как оплатишь - нажимай кнопку, и напоминания прекратятся до следующего месяца."
        )
    else:
        await message.answer("Этот бот предназначен для другого пользователя.")


# ===== ЗАПУСК ПЛАНИРОВЩИКА =====
async def on_startup():
    # Задача на каждый день: проверяем, надо ли напоминать
    scheduler.add_job(daily_reminder_task, "cron", hour=REMINDER_TIME_HOUR, minute=REMINDER_TIME_MINUTE)
    # Задача на 1-е число каждого месяца: сбрасываем статус
    scheduler.add_job(reset_paid_status, "cron", day=1, hour=0, minute=1)
    scheduler.start()
    print("Планировщик запущен.")

    # Проверяем статус при запуске (если сегодня уже нужно напоминать)
    await check_date_and_remind()


# ===== ТОЧКА ВХОДА =====
async def main():
    print("Бот запущен...")
    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())