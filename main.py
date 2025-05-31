import asyncio
import logging
import sqlite3
from random import randint
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InputFile, ReplyKeyboardMarkup, InlineKeyboardMarkup, KeyboardButton, InlineKeyboardButton
import re

menu = ReplyKeyboardMarkup(keyboard=[

        [KeyboardButton(text="Начать"),
        KeyboardButton(text="Помощь")],
        [KeyboardButton(text='Выбрать язык'),
        KeyboardButton(text="Выбрать способ изучения")],
        [KeyboardButton(text="Посмотреть прогресс"),
        KeyboardButton(text='Стереть прогресс')]

], resize_keyboard=True, one_time_keyboard=False)

language_choose = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Английский 🇬🇧", callback_data="lang_en"),
        InlineKeyboardButton(text="Немецкий 🇩🇪", callback_data="lang_de"),
        InlineKeyboardButton(text="Испанский 🇪🇦", callback_data="lang_ea"),
    ],
    [
        InlineKeyboardButton(text="Помощь", callback_data="help_lang")
    ]
])

activity_choose = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Тест 📝", callback_data="test"),
        InlineKeyboardButton(text="Учить слова 📖", callback_data="learn_words"),
        InlineKeyboardButton(text="Учить правила 📚", callback_data="learn_rules")
    ],
    [
        InlineKeyboardButton(text="Помощь", callback_data="help_act")
    ]
])

restart_button = InlineKeyboardMarkup(inline_keyboard=[
    [
    ],
    [
        InlineKeyboardButton(text="Стереть", callback_data="restart"),
        InlineKeyboardButton(text="Отмена", callback_data="cancel")
    ]
])


class DataBase:
    def __init__(self):
        self.db_path = "main_data.db"
        self._create_tables()

    def _create_tables(self):
        """Создаем таблицы, если они не существуют"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    is_new BOOL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_statistic (
                    user_id INTEGER PRIMARY KEY,
                    current_language TEXT DEFAULT 'нет',
                    waiting_for_answers BOOLEAN DEFAULT 0, 
                    tests_solved INTEGER DEFAULT '0',
                    test_answers TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            cursor.execute("""
                            CREATE TABLE IF NOT EXISTS english_tests (
                                test_number INTEGER,
                                test_theme TEXT,
                                test TEXT,
                                correct_answers TEXT

                            )
                        """)
            conn.commit()
            cursor.execute("""
                                        CREATE TABLE IF NOT EXISTS german_tests (
                                            test_number INTEGER,
                                            test_theme TEXT,
                                            test TEXT,
                                            correct_answers TEXT

                                        )
                                    """)
            conn.commit()
            cursor.execute("""
                                                    CREATE TABLE IF NOT EXISTS spanish_tests (
                                                        test_number INTEGER,
                                                        test_theme TEXT,
                                                        test TEXT,
                                                        correct_answers TEXT

                                                    )
                                                """)
            conn.commit()
            cursor.execute("""
                                        CREATE TABLE IF NOT EXISTS theory (
                                            language TEXT,
                                            site TEXT,
                                            words TEXT

                                        )
                                    """)
            conn.commit()

    def show_test(self, value, table):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(f"SELECT test FROM {table} WHERE test_number = ?", (value,))
                result = cursor.fetchone()
                return result if result else None
            except sqlite3.Error as e:
                logging.error(f"Ошибка при выборе данных: {e}")
                return None

    def _get_connection(self):
        """Возвращает новое соединение с базой данных"""
        return sqlite3.connect(self.db_path)

    def add_new_data(self, table, form, *rows):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(f"INSERT OR REPLACE INTO {table} VALUES{form}", (rows))
                conn.commit()
            except sqlite3.Error as e:
                logging.error(f"Ошибка при добавлении данных: {e}")

    def delete_data(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM user_statistic WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
            except sqlite3.Error as e:
                logging.error(f"Ошибка при добавлении данных: {e}")

    def choose_data(self, table, searched_obj, row, value):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(f"SELECT {searched_obj} FROM {table} WHERE {row} = ?", (value,))
                result = cursor.fetchone()
                return result[0] if result else None
            except sqlite3.Error as e:
                logging.error(f"Ошибка при выборе данных: {e}")
                return None


class AssistantLinguist:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self._register_handlers()
        self.language_menu = language_choose
        self.activity_menu = activity_choose
        self.restart_menu = restart_button
        self.main_menu = menu
        self.comands = ["Начать", "Помощь", "Выбрать язык", "Выбрать способ изучения", "Посмотреть прогресс", "Стереть прогресс"]


    def _register_handlers(self):
        """Регистрируем обработчики сообщений"""
        self.dp.message.register(self._send_welcome, Command("start"))
        self.dp.message.register(self._send_help, Command("help"))
        self.dp.message.register(self._send_restart, Command("restart"))
        self.dp.message.register(self._send_stats, Command("stats"))
        self.dp.message.register(self._send_language_list, Command("language"))
        self.dp.message.register(self._send_activity_list, Command("activity"))

        self.dp.message.register(self._handle_message)
        self.dp.message.register(self._show_test)

        self.dp.callback_query.register(self._handle_language_buttons,
                                        lambda c: c.data in ["lang_en", "lang_de", "lang_ea", "help_lang"])
        self.dp.callback_query.register(self._handle_activity_buttons,
                                        lambda c: c.data in ["test", "learn_words", "learn_rules", "help_act"])
        self.dp.callback_query.register(self._handle_restart_button,
                                        lambda c: c.data in ["restart", "cancel"])

    async def _send_stats(self, message: types.Message):
        user_id = message.from_user.id
        lang = DB.choose_data("user_statistic", "current_language", "user_id", user_id)
        tests_count = (DB.choose_data("user_statistic", "tests_solved", "user_id", user_id))
        if DB.choose_data("user_statistic", "user_id", "user_id", user_id) is None:
            stats = ('Пользователь не найден!')
        else:
            stats = (
                "Вот ваш прогресс:\n"
                f'Текущий изучаемый язык: {lang}\n'
                f'тестов, решенных без ошибок: {tests_count}'

            )
        await message.answer(stats)

    async def _send_activity_list(self, message: types.Message):
        """Отправляет меню активностей"""
        user_id = message.from_user.id
        lang = (DB.choose_data("user_statistic", "current_language", "user_id", user_id))
        if lang is not None and lang != "нет":
            await message.answer("Выберите способ изучения языка", reply_markup=self.activity_menu)
        else:
            await message.answer("Вы еще не выбрали ни один язык для изучения!")

    async def _send_language_list(self, message: types.Message):
        """Отправляет меню выбора языка"""
        user_id = message.from_user.id
        if DB.choose_data("user_statistic", "user_id", "user_id", user_id) is None:
            await message.answer('Пользователь не найден!')
        else:
            await message.answer("Выберите язык из доступных:", reply_markup=self.language_menu)

    async def _send_restart(self, message: types.Message):
        """Отправляет меню выбора языка"""
        await message.answer("Вы хотите стереть весь текущий прогресс?", reply_markup=self.restart_menu)



    async def _handle_restart_button(self, callback_query: types.CallbackQuery):
        data = callback_query.data
        user_id = callback_query.from_user.id
        message_id = callback_query.message.message_id
        await self.bot.delete_message(chat_id=user_id, message_id=message_id)
        if data == "restart":

            DB.delete_data(user_id)
            await self.bot.send_message(user_id, "Ваш прогресс стерт!")
            self.messages_count = 0
        elif data == "cancel":
            await self.bot.send_message(user_id,
                                        "Хорошо, но вы всегда можете удалить текущий прогресс, если захотите! 😉")

    async def _handle_activity_buttons(self, callback_query: types.CallbackQuery):
        """Обработчик кнопок активностей"""
        data = callback_query.data
        user_id = callback_query.from_user.id
        message_id = callback_query.message.message_id

        try:
            await self.bot.delete_message(chat_id=user_id, message_id=message_id)
            lang = DB.choose_data("user_statistic", "current_language", "user_id", user_id)
            tests_count = (DB.choose_data("user_statistic", "tests_solved", "user_id", user_id))
            DB.add_new_data("user_statistic", "(?, ?, ?, ?, ?)", user_id, lang, False, tests_count, None)
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения: {e}")

        if data == "test":
            await self._show_test(callback_query)
        elif data == "learn_words":
            words = DB.choose_data("theory", "words", "language", lang)
            words_lst = []
            for row in words.split("\n"):
                line = "".join(str(item) for item in row)
                words_lst.append(line)
            await self.bot.send_message(user_id, '\n'.join(words_lst))
        elif data == "learn_rules":

            site = DB.choose_data("theory", "site", "language", lang)
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Открыть сайт", url=site)]
            ])
            await self.bot.send_message(
                callback_query.from_user.id,
                f"Ссылка на сайт с правилами выбранного языка: {site}",
                reply_markup=markup
            )
        elif data == "help_act":
            await self.bot.send_message(user_id,
                                        "Вам необходимо выбрать, каким способ вы хотите начать/продолжить изучать выбранный язык")

        await callback_query.answer()

    async def _show_test(self, callback_query: types.CallbackQuery):
        user_id = callback_query.from_user.id
        test_number = randint(1, 5)
        lang = DB.choose_data("user_statistic", "current_language", "user_id", user_id)
        if lang == "Английский":
            theme = DB.choose_data("english_tests", "test_theme", "test_number", test_number)
            test_data = DB.show_test(test_number, "english_tests")
            correct_answers = DB.choose_data("english_tests", "correct_answers", "test_number", test_number)
        elif lang == "Немецкий":
            theme = DB.choose_data("german_tests", "test_theme", "test_number", test_number)
            test_data = DB.show_test(test_number, "german_tests")
            correct_answers = DB.choose_data("german_tests", "correct_answers", "test_number", test_number)
        elif lang == "Испанский":
            theme = DB.choose_data("spanish_tests", "test_theme", "test_number", test_number)
            test_data = DB.show_test(test_number, "spanish_tests")
            correct_answers = DB.choose_data("spanish_tests", "correct_answers", "test_number", test_number)

        tests_count = (DB.choose_data("user_statistic", "tests_solved", "user_id", user_id))
        DB.add_new_data("user_statistic", "(?, ?, ?, ?, ?)", user_id, lang, True, tests_count, correct_answers)
        message_lines = [f"Тест по теме {theme}:"]


        for row in test_data:
            line = "".join(str(item) for item in row)
            message_lines.append(line)

        message_lines.append('\n' +
            'Напишите ответы ниже в одно сообщение (каждый ответ с новой строки)')

        await self.bot.send_message(user_id, "\n".join(message_lines))
        await callback_query.answer()

    async def _handle_language_buttons(self, callback_query: types.CallbackQuery):
        """Обработчик кнопок выбора языка"""
        data = callback_query.data
        user_id = callback_query.from_user.id
        message_id = callback_query.message.message_id

        await self.bot.delete_message(chat_id=user_id, message_id=message_id)

        if data == "lang_en":
            Choosed_lang = "Английский"
            await self.bot.send_message(user_id, "Вы выбрали английский язык! 🇬🇧")
        elif data == "lang_de":
            Choosed_lang = "Немецкий"
            await self.bot.send_message(user_id, "Вы выбрали немецкий язык! 🇩🇪")
        elif data == "lang_ea":
            Choosed_lang = "Испанский"
            await self.bot.send_message(user_id, "Вы выбрали Испанский язык! 🇪🇦")

        elif data == "help_lang":

            await self.bot.send_message(user_id,
                                        "Вы можете легко переключаться между языками и изучать их! ")

        tests_count = (DB.choose_data("user_statistic", "tests_solved", "user_id", user_id))
        DB.add_new_data("user_statistic", "(?, ?, ?, ?, ?)", user_id, Choosed_lang, False, tests_count, None)
        await callback_query.answer()


    async def _handle_message(self, message: types.Message):
        user_id = message.from_user.id
        if DB.choose_data("user_statistic", "waiting_for_answers", "user_id", user_id) and message.text.split('\n')[0] not in self.comands:
            user_answers = message.text.split('\n')

            checked_message = []
            correct = 0
            test_ans = DB.choose_data("user_statistic", "test_answers", "user_id", user_id).split('\n')
            if len(user_answers) < len(test_ans):
                for i in range(len(test_ans) - len(user_answers)):
                    user_answers.append("")
            for i in range(len(test_ans)):
                s = re.sub("[^A-Za-z]", "", user_answers[i].strip()).lower()
                s2 = re.sub("[^A-Za-z]", "", test_ans[i].strip()).lower()
                if s == s2:
                    checked_message.append(f"{test_ans[i]} ✅ Верно!")
                    correct += 1
                else:
                    checked_message.append(f"{user_answers[i]} ❌ Неверно. Правильный ответ: {test_ans[i]}")

            await message.answer("\n".join(checked_message))
            test_count = (DB.choose_data("user_statistic", "tests_solved", "user_id", user_id))
            Choosed_lang = (DB.choose_data("user_statistic", "current_language", "user_id", user_id))
            if correct == len(test_ans):
                test_count += 1
            DB.add_new_data("user_statistic", "(?, ?, ?, ?, ?)", user_id, Choosed_lang, False, test_count, None)
        else:
            text = message.text.lower()
            if DB.choose_data("user_statistic", "user_id", "user_id", user_id):
                test_count = (DB.choose_data("user_statistic", "tests_solved", "user_id", user_id))
                Choosed_lang = (DB.choose_data("user_statistic", "current_language", "user_id", user_id))
                DB.add_new_data("user_statistic", "(?, ?, ?, ?, ?)", user_id, Choosed_lang, False, test_count, None)
            if text == "начать":
                await self._send_welcome(message)
            elif text == "помощь":
                await self._send_help(message)
            elif text == "выбрать язык":
                await self._send_language_list(message)
            elif text == "выбрать способ изучения":
                await self._send_activity_list(message)
            elif text == "посмотреть прогресс":
                await self._send_stats(message)
            elif text == "стереть прогресс":
                await self._send_restart(message)
            else:
                await message.answer(
                    f"Я пока не понимаю эту команду. Попробуйте /help.")


    async def _send_welcome(self, message: types.Message):
        """Обработчик команды /start"""

        user_id = message.from_user.id
        user = message.from_user
        username = user.first_name

        DB.add_new_data("users", "(?, ?)", user_id, username)
        if DB.choose_data("user_statistic", "user_id", "user_id", user_id) is None:
            DB.add_new_data("user_statistic", "(?, ?, ?, ?, ?)", user_id, 'нет', False, 0, None)

        start_msg = f"Привет, {username}! 👋\n\n" \
                          f"Я – ваш персональный помощник в изучении языков! 🌍📚\n\n" \
                          f"Чем могу помочь?\n" \
                          f"В моей базе собраны полезные и эффективные тесты для проверки знаний\n" \
                          f"Также на проверенных сайтах вы сможете найти всю теорию выбранного вами языка!\n" \
                          f"Как это работает? Все просто!\n" \
                          f"Выбирайте язык\n" \
                          f"Решайте тесты и изучайте теорию\n" \
                          f"Улучшайте свои навыки день за днём!\n\n" \
                          f"Готовы начать? Поехали! 🚀\n\n" \
                          f"(Просто выберите, какой язык хотите учить. доступны три языка: английский, немецкий и испанский) 😊\n"

        await message.answer(start_msg, reply_markup=self.main_menu)

    async def _send_help(self, message: types.Message):
        """Обработчик команды /help"""
        help_text = (
            "Доступные команды:\n"
            "/start - начать работу\n"
            "/help - помощь\n"
            "/language - выбрать язык\n"
            "/activity - выбрать активность\n"
            "/restart - стереть прогресс\n"
            "/stats - прогресс"
        )
        await message.answer(help_text)

    async def start(self):
        """Запускает бота"""

        try:
            logging.info("Бот запущен!")
            await self.dp.start_polling(self.bot)
        finally:
            await self.bot.close()


if __name__ == '__main__':
    """вместо TOKEN необходимо подставить токен бота в телеграм"""
    DB = DataBase()

    API_TOKEN = TOKEN
    logging.basicConfig(level=logging.INFO)
    app = AssistantLinguist(API_TOKEN)

    asyncio.run(app.start())
