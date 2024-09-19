import streamlit as st
import base64
import ssl
import psycopg2.extensions

# Отримання секретів з Streamlit
DB_USERNAME = st.secrets["DB_USERNAME"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_HOST = st.secrets["DB_HOST"]
DB_NAME = st.secrets["DB_NAME"]
DB_PORT = st.secrets["DB_PORT"]
SSL_MODE = st.secrets["SSL_MODE"]
DB_SSL_ROOT_CERT_BASE64 = st.secrets["DB_SSL_ROOT_CERT"]

# Декодування SSL сертифіката
ssl_cert_decoded = base64.b64decode(DB_SSL_ROOT_CERT_BASE64)

# Створюємо SSL-контекст із сертифікатом
ssl_context = ssl.create_default_context(cadata=ssl_cert_decoded.decode("utf-8"))

# Підключення до бази даних за допомогою SSL-контексту
conn = psycopg2.connect(
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USERNAME,
    password=DB_PASSWORD,
    port=DB_PORT,
    sslmode=SSL_MODE,
    sslrootcert=ssl_context
)

# Тестовий запит
cursor = conn.cursor()
cursor.execute("SELECT version();")
db_version = cursor.fetchone()

# Виведення результату
st.write(f"Database version: {db_version[0]}")

# Закриваємо з'єднання
cursor.close()
conn.close()