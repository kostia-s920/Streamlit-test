import streamlit as st
import psycopg2
import base64

# Отримуємо секрети з Streamlit
DB_USERNAME = st.secrets["db_username"]
DB_PASSWORD = st.secrets["db_password"]
DB_HOST = st.secrets["db_host"]
DB_PORT = st.secrets["db_port"]
DB_NAME = st.secrets["db_name"]
SSL_MODE = st.secrets["ssl_mode"]
DB_SSL_ROOT_CERT = st.secrets["db_ssl_root_cert"]

# Декодуємо SSL сертифікат
ssl_cert_decoded = base64.b64decode(DB_SSL_ROOT_CERT)

# Збереження сертифікату в тимчасовий файл
with open("/tmp/ca.pem", "wb") as f:
    f.write(ssl_cert_decoded)

# Підключення до бази даних
try:
    connection = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode=SSL_MODE,
        sslrootcert="/tmp/ca.pem"
    )
    st.write("Підключення до бази даних успішне!")
except Exception as e:
    st.write("Помилка підключення до бази даних:", str(e))