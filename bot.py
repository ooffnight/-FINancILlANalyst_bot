
import logging
import sqlite3
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler
from prettytable import PrettyTable


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


conn = sqlite3.connect('expenses.db')
cursor = conn.cursor()


cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        user_id INTEGER,
        amount REAL,
        category TEXT,
        description TEXT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS budget (
        user_id INTEGER,
        budget_amount REAL
    )
''')
conn.commit()


async def start(update: Update, context: CallbackContext) -> None:
    """Отправка приветственного сообщения и кнопок выбора категории"""
    keyboard = [
        [InlineKeyboardButton("Еда", callback_data="Еда"),
         InlineKeyboardButton("Транспорт", callback_data="Транспорт"),
         InlineKeyboardButton("Развлечения", callback_data="Развлечения")],
        [InlineKeyboardButton("Другие расходы", callback_data="Другие расходы"),
         InlineKeyboardButton("Показать все расходы", callback_data="Показать все расходы")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я бот для отслеживания твоих расходов.\nВыберите категорию или команду:\n /add - нужно ввести сумму категорию описание\n /expenses - отображает все расходы\n /category_report - отправляет картинку с графиком",
        reply_markup=reply_markup
    )

async def button(update: Update, context: CallbackContext) -> None:
    """Обработка нажатия на кнопки"""
    query = update.callback_query
    await query.answer()
   
    if query.data == "Показать все расходы":
        await show_expenses(update, context)
    else:
       
        await add_expense(update, context, category=query.data)

async def add_expense(update: Update, context: CallbackContext, category: str = None) -> None:
    """Добавление расхода с категорией"""
    
    
    if not context.args or len(context.args) < 1:
        await update.callback_query.answer("Использование: /add <сумма>", show_alert=True)
        return
    
    try:
        amount = float(context.args[0])
        description = " ".join(context.args[1:]) if len(context.args) > 1 else "Без описания"
        
        if amount <= 0:
            await update.callback_query.answer("Сумма расхода должна быть положительной.", show_alert=True)
            return
        
       
        cursor.execute("INSERT INTO expenses (user_id, amount, category, description) VALUES (?, ?, ?, ?)",
                       (update.callback_query.from_user.id, amount, category, description))
        conn.commit()
        
       
        await update.callback_query.answer(f"Расход в размере {amount} добавлен.\nКатегория: {category}\nОписание: {description}", show_alert=True)
    
    except ValueError:
        await update.callback_query.answer("Ошибка при добавлении расхода. Убедитесь, что сумма указана числом.", show_alert=True)
async def show_expenses(update: Update, context: CallbackContext) -> None:
    """Показать все расходы пользователя"""
    cursor.execute("SELECT amount, category, description, date FROM expenses WHERE user_id=?", (update.message.from_user.id,))
    expenses = cursor.fetchall()
    if not expenses:
        await update.message.reply_text("Нет расходов для отображения.")
        return
    
    table = PrettyTable()
    table.field_names = ["Сумма", "Категория", "Описание", "Дата"]
    for exp in expenses:
        table.add_row(exp)
    await update.message.reply_text(f"Ваши расходы:\n{table}")

async def show_category_report(update: Update, context: CallbackContext) -> None:
    """Показать расходы по категориям"""
    cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id=? GROUP BY category", (update.message.from_user.id,))
    category_data = cursor.fetchall()
    if not category_data:
        await update.message.reply_text("Нет данных по категориям.")
        return
   
    categories = [data[0] for data in category_data]
    amounts = [data[1] for data in category_data]
    plt.bar(categories, amounts)
    plt.title("Расходы по категориям")
    plt.xlabel("Категории")
    plt.ylabel("Сумма")
    plt.savefig("category_report.png")
    plt.close()
    await update.message.reply_photo(photo=open("category_report.png", "rb"), caption="График расходов по категориям")

async def set_budget(update: Update, context: CallbackContext) -> None:
    """Установка бюджета"""
    try:
        budget = float(context.args[0])
        cursor.execute("INSERT INTO budget (user_id, budget_amount) VALUES (?, ?)",
                       (update.message.from_user.id, budget))
        conn.commit()
        await update.message.reply_text(f"Бюджет на месяц установлен: {budget} рублей.")
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /set_budget <сумма>")

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token("8380768654:AAEPrn6sbtIYN0TpTKs0JH_sKerhDvAhUO0").build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_expense))
    application.add_handler(CommandHandler("expenses", show_expenses))
    application.add_handler(CommandHandler("set_budget", set_budget))
    application.add_handler(CommandHandler("category_report", show_category_report))
    
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()

if __name__ == "__main__":
    main()