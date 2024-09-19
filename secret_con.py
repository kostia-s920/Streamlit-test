import os
import base64
import streamlit as st

# Отримуємо секрети
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
SSL_MODE = os.getenv('SSL_MODE')
DB_SSL_ROOT_CERT = os.getenv('DB_SSL_ROOT_CERT')

# Функція для тестування секретів
def test_secrets():
    # Виведення значень для тестування
    st.write("DB_USERNAME:", DB_USERNAME)
    st.write("DB_PASSWORD:", DB_PASSWORD)
    st.write("DB_HOST:", DB_HOST)
    st.write("DB_NAME:", DB_NAME)
    st.write("DB_PORT:", DB_PORT)
    st.write("SSL_MODE:", SSL_MODE)

    # Тест декодування сертифікату з Base64
    try:
        ssl_cert_decoded = base64.b64decode(DB_SSL_ROOT_CERT)
        st.write("SSL Root Certificate decoded successfully!")
        # Виведемо перші 100 символів сертифікату для підтвердження
        st.write(ssl_cert_decoded[:100])
    except Exception as e:
        st.write("Error decoding SSL Root Certificate:", str(e))

# Запустити функцію тестування
if __name__ == "__main__":
    st.title("Test Streamlit Secrets")
    test_secrets()