import streamlit as st
import psycopg2


# Функція для підключення до бази даних PostgreSQL
def connect_to_db():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="competitor_content",
            user="kostia.s920",
            password="1502"
        )
        return connection
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

# Функція для перевірки авторизаційних даних
def check_credentials(username, password, conn):
    try:
        # Створюємо курсор для виконання запитів
        cur = conn.cursor()

        # SQL запит для перевірки, чи існує користувач з введеними даними
        query = """
        SELECT * FROM users
        WHERE username = %s AND password = crypt(%s, password)
        """
        cur.execute(query, (username, password))

        # Якщо користувач знайдений
        if cur.fetchone():
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error during authorization: {e}")
        return False

# Головна функція
def main():
    st.title("Авторизація")

    # Підключення до бази даних
    conn = connect_to_db()

    # Якщо підключення до бази даних успішне
    if conn:
        # Вікно для вводу логіну і паролю
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        # Кнопка для авторизації
        if st.button("Login"):
            # Перевірка логіну та паролю
            if check_credentials(username, password, conn):
                st.success("Авторизація успішна!")
                # Показати доступ до даних або інші функції після успішної авторизації
                st.write("Тепер ви можете переглянути дані.")
                # Тут можна додати код для відображення інтерфейсу програми після авторизації
            else:
                st.error("Невірний логін або пароль")

    # Закриваємо з'єднання з базою даних після завершення
    if conn:
        conn.close()

if __name__ == "__main__":
    main()