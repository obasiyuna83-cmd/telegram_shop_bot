import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import database as db

# Рекомендуется использовать переменные окружения или локальный файл конфигурации.
try:
    import config
    BOT_TOKEN = config.config.BOT_TOKEN if hasattr(config, 'config') else config.BOT_TOKEN
except ImportError:
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

dp = Dispatcher()

# ГЛАВНОЕ МЕНЮ
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛍 Каталог товаров", callback_data="catalog"),
        ],
        [
            InlineKeyboardButton(text="📞 Связаться с поддержкой", callback_data="support"),
            InlineKeyboardButton(text="ℹ️ О нас", callback_data="about")
        ]
    ])
    return keyboard

# СТАРТОВЫЙ ОБРАБОТЧИК
@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Регистрация пользователя в БД
    await db.add_user(message.from_user.id, message.from_user.username)
    
    welcome_text = (
        f"👋 Приветствуем, *{message.from_user.full_name}* в нашем демо-магазине!\n\n"
        "Этот бот — пример профессионального портфолио фрилансера. "
        "Здесь реализован каталог товаров, корзина заказов и интеграция с базой данных.\n\n"
        "Выберите интересующий вас пункт меню ниже 👇"
    )
    await message.answer(
        welcome_text, 
        reply_markup=get_main_menu(), 
        parse_mode=ParseMode.MARKDOWN
    )

# КАТАЛОГ
@dp.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    products = await db.get_products()
    
    keyboard_buttons = []
    for product in products:
        # Кнопка для каждого товара
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{product['name']} — {product['price']} ₽", 
                callback_data=f"prod_{product['id']}"
            )
        ])
    
    # Кнопка возврата в меню
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        "📦 *Каталог наших услуг и товаров:*\n\nВыберите позицию для просмотра подробностей:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

# КАРТОЧКА ТОВАРА
@dp.callback_query(F.data.startswith("prod_"))
async def show_product_detail(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = await db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("Товар не найден!", show_alert=True)
        return
    
    text = (
        f"📦 *{product['name']}*\n\n"
        f"📝 *Описание:* {product['description']}\n\n"
        f"💰 *Цена:* {product['price']} ₽"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Купить в один клик", callback_data=f"buy_{product['id']}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data="catalog")
        ]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

# ПОКУПКА
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = await db.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("Ошибка при покупке!", show_alert=True)
        return
    
    # Создание заказа в БД
    await db.create_order(callback.from_user.id, product_id)
    
    # Отправка уведомления администратору (@vincaren)
    admin_username = "vincaren"
    admin_id = await db.get_user_by_username(admin_username)
    if admin_id:
        admin_text = (
            f"🔔 *Новый заказ!*\n\n"
            f"👤 *Покупатель:* @{callback.from_user.username or 'без юзернейма'} (ID: {callback.from_user.id})\n"
            f"📝 *Имя:* {callback.from_user.full_name}\n"
            f"📦 *Товар:* {product['name']}\n"
            f"💰 *Сумма:* {product['price']} ₽"
        )
        try:
            await callback.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление админу: {e}")
    else:
        logging.warning(f"Администратор @{admin_username} еще не запускал бота и отсутствует в БД.")
    
    success_text = (
        f"🎉 *Заказ успешно оформлен!*\n\n"
        f"Вы выбрали: *{product['name']}*\n"
        f"Сумма к оплате: *{product['price']} ₽*\n\n"
        f"Наш менеджер свяжется с вами в Telegram в ближайшее время. Спасибо за заказ!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
        ]
    ])
    
    await callback.message.edit_text(
        success_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

# ИНФОРАМАЦИЯ О НАС
@dp.callback_query(F.data == "about")
async def show_about(callback: CallbackQuery):
    about_text = (
        "ℹ️ *Информация о разработчике:*\n\n"
        "Этот бот создан в демонстрационных целях для портфолио фриланс-разработчика.\n\n"
        "🛠 *Стек технологий:* Python, aiogram 3.x, SQLite (aiosqlite).\n"
        "🤖 Бот поддерживает асинхронную работу, готов к развертыванию на любом VPS сервере и легко расширяется под задачи вашего бизнеса."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        about_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

# ПОДДЕРЖКА
@dp.callback_query(F.data == "support")
async def show_support(callback: CallbackQuery):
    support_text = (
        "📞 *Связь с поддержкой:*\n\n"
        "Если у вас возникли вопросы по работе бота или вы хотите заказать подобное решение для своего бизнеса:\n\n"
        "✍ Напишите мне в личные сообщения: @vincaren"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        support_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

# ВОЗВРАТ В ГЛАВНОЕ МЕНЮ
@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    welcome_text = (
        f"👋 Приветствуем, *{callback.from_user.full_name}* в нашем демо-магазине!\n\n"
        "Этот бот — пример профессионального портфолио фрилансера. "
        "Здесь реализован каталог товаров, корзина заказов и интеграция с базой данных.\n\n"
        "Выберите интересующий вас пункт меню ниже 👇"
    )
    await callback.message.edit_text(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

# ОСНОВНОЙ ЗАПУСК
async def main():
    # Инициализация базы данных
    await db.init_db()
    
    # Проверка токена
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not BOT_TOKEN:
        print("\n" + "="*60)
        print("ВНИМАНИЕ! Вы не указали токен вашего Telegram-бота в файле bot.py.")
        print("1. Создайте бота через @BotFather в Telegram.")
        print("2. Скопируйте полученный API токен.")
        print("3. Вставьте его в переменную BOT_TOKEN на строке 11 в файле bot.py.")
        print("="*60 + "\n")
        return

    # Запуск логирования
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Создание бота и запуск поллинга
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    print("Бот успешно запущен и ожидает сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
