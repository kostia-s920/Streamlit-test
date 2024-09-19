import streamlit as st
import base64

# Отримання секретів з Streamlit
DB_USERNAME = st.secrets["DB_USERNAME"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_HOST = st.secrets["DB_HOST"]
DB_NAME = st.secrets["DB_NAME"]
DB_PORT = st.secrets["DB_PORT"]
SSL_MODE = st.secrets["SSL_MODE"]
DB_SSL_ROOT_CERT_BASE64 = st.secrets["DB_SSL_ROOT_CERT"]

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

# Запустити функцію тестування
if __name__ == "__main__":
    st.title("Test Streamlit Secrets")