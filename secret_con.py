import streamlit as st
import psycopg2
import base64

# Отримання секретів з Streamlit (назви повинні відповідати тому, що вказано в secrets.toml)
DB_USERNAME = st.secrets["db_username"]
DB_PASSWORD = st.secrets["db_password"]
DB_HOST = st.secrets["db_host"]
DB_NAME = st.secrets["db_name"]
DB_PORT = st.secrets["db_port"]
SSL_MODE = st.secrets["ssl_mode"]
DB_SSL_ROOT_CERT_BASE64 = st.secrets["db_ssl_root_cert"]

# Декодування SSL сертифіката
try:
    ssl_cert_decoded = base64.b64decode(DB_SSL_ROOT_CERT_BASE64)
    st.write("SSL Root Certificate decoded successfully!")
    st.write(ssl_cert_decoded[:100])  # Виведемо перші 100 символів для тестування
except Exception as e:
    st.write("Error decoding SSL Root Certificate:", str(e))

# Виведення для тестування секретів
st.title("Test Streamlit Secrets")
st.write("DB_USERNAME:", DB_USERNAME)
st.write("DB_PASSWORD:", DB_PASSWORD)
st.write("DB_HOST:", DB_HOST)
st.write("DB_NAME:", DB_NAME)
st.write("DB_PORT:", DB_PORT)
st.write("SSL_MODE:", SSL_MODE)