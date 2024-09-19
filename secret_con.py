import streamlit as st
import psycopg2
import base64

# Отримання секретів
DB_USERNAME = st.secrets["DB_USERNAME"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_HOST = st.secrets["DB_HOST"]
DB_NAME = st.secrets["DB_NAME"]
DB_PORT = st.secrets["DB_PORT"]
SSL_MODE = st.secrets["SSL_MODE"]
DB_SSL_ROOT_CERT_BASE64 = st.secrets["DB_SSL_ROOT_CERT"]

# Декодування SSL сертифіката
ssl_cert_decoded = base64.b64decode(DB_SSL_ROOT_CERT_BASE64)

# Запис сертифіката в тимчасовий файл
with open("ca_cert.pem", "wb") as f:
    f.write(ssl_cert_decoded)

# Підключення до бази даних
conn = psycopg2.connect(
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USERNAME,
    password=DB_PASSWORD,
    port=DB_PORT,
    sslmode=SSL_MODE,
    sslrootcert="ca_cert.pem"
)

# Тестовий запит
cursor = conn.cursor()
cursor.execute("SELECT version();")
db_version = cursor.fetchone()

# Виведення результату
st.write(f"Database version: {db_version[0]}")