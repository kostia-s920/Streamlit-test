import streamlit as st
import psycopg2
import hashlib


# Функція для підключення до бази даних PostgreSQL
def connect_to_db():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="competitor_content",
            user="admin",  # Користувач бази даних
            password="password"  # Пароль користувача
        )
        return connection
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None


# Функція для хешування пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Функція для перевірки облікових даних
def check_credentials(username, password, conn):
    hashed_password = hash_password(password)
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    cursor.execute(query, (username, hashed_password))
    result = cursor.fetchone()
    cursor.close()
    return result is not None


# Функція для створення сторінки авторизації
def login(conn):
    st.title("Авторизація")

    # Форма для введення облікових даних
    username = st.text_input("Ім'я користувача")
    password = st.text_input("Пароль", type="password")

    if st.button("Увійти"):
        if username and password:
            if check_credentials(username, password, conn):
                st.success(f"Вітаємо, {username}! Ви успішно увійшли в систему.")
                return True
            else:
                st.error("Неправильне ім'я користувача або пароль.")
        else:
            st.error("Будь ласка, введіть ім'я користувача та пароль.")

    return False


# Основна функція застосунку
def main_app(conn):
    st.title("Головна сторінка")
    st.write("Ви увійшли в систему і тепер можете використовувати застосунок.")
    # Тут можна додати основну логіку застосунку, яка використовує дані з бази


# Основна функція для запуску застосунку
def main():
    conn = connect_to_db()

    if conn:
        # Якщо користувач авторизований, показати головну сторінку, інакше показати авторизацію
        if login(conn):
            main_app(conn)
        else:
            st.warning("Вам потрібно увійти, щоб отримати доступ до застосунку.")


if __name__ == "__main__":
    main()