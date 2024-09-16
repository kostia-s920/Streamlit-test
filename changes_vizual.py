import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
import matplotlib.pyplot as plt

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

# Function to fetch data from the PostgreSQL database
def fetch_data(conn, query):
    df = pd.read_sql_query(query, conn)
    return df

# Function to create the CSS style
def create_css_style():
    st.markdown("""
        <style>
        .contribution-graph {
            display: grid;
            grid-template-columns: repeat(53, 12px);
            grid-gap: 3px;
            justify-content: center;
            align-items: center;
            position: relative;
        }
        .contribution-square {
            width: 10px;
            height: 10px;
            background-color: #ebedf0;
            border-radius: 2px;
            position: relative;
        }
        .contribution-square[data-level="1"] { background-color: #c6e48b; }
        .contribution-square[data-level="2"] { background-color: #7bc96f; }
        .contribution-square[data-level="3"] { background-color: #239a3b; }
        .contribution-square[data-level="4"] { background-color: #196127; }
        .contribution-square:hover {
            transform: scale(1.2);
            cursor: pointer;
        }
        .tooltip {
            position: absolute;
            background-color: #333;
            color: #fff;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;   
            visibility: hidden;
            z-index: 10;
            transition: visibility 0.3s, opacity 0.3s ease;
            opacity: 0;
        }
        .contribution-square:hover .tooltip {
            visibility: visible;
            opacity: 1;
        }
        .total-changes {
            font-size: 1.2em;
            font-weight: bold;
            color: #0b3d13;
            text-align: center;
            margin-top: 10px;
        }
        .month-label {
            text-align: center;
            font-size: 0.8em;
            color: #666;
            margin-bottom: 4px;
        }
        </style>
    """, unsafe_allow_html=True)

# Function to display the month labels
def display_month_labels():
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    st.markdown("<div class='contribution-graph'>", unsafe_allow_html=True)
    for month in months:
        st.markdown(f"<div class='month-label'>{month}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Function to display the contribution graph
def display_contribution_graph(df):
    # Group data by date and count changes
    changes_by_day = df.groupby(df['change_date'].dt.date).count()

    # Create a matrix to represent changes by day (7 days a week, 53 weeks a year)
    changes_matrix = np.zeros((7, 53))

    # Fill the matrix with changes
    for day, count in changes_by_day.iterrows():
        week = day.isocalendar()[1] - 1  # Get week number
        weekday = day.weekday()  # Get weekday (0 = Monday, 6 = Sunday)
        changes_matrix[weekday, week] = count['changes']  # Number of changes

    # Create the graph
    fig, ax = plt.subplots(figsize=(12, 3))  # Adjust graph size

    # Display the changes matrix
    cax = ax.matshow(changes_matrix, cmap='Greens', aspect='auto')

    # Add months as labels along the X-axis
    ax.set_yticks(range(7))
    ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])

    # Set correct positions for months (12 labels for 53 weeks, approximately every 4 weeks)
    ax.set_xticks([4, 8, 13, 17, 22, 26, 31, 35, 40, 44, 48, 52])
    ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])

    # Remove frames for better appearance
    ax.spines[:].set_visible(False)

    # Add a color scale to show the number of changes
    fig.colorbar(cax)

    # Show the total number of changes
    total_changes = int(changes_by_day['changes'].sum())
    st.subheader(f"Total Changes: {total_changes}")

    st.pyplot(fig)

# Main function
def main():
    st.title("Visualization of Content Changes")

    # Connect to the database
    conn = connect_to_db()

    if conn:
        competitors = ['docebo_com', 'ispringsolutions_com', 'talentlms_com', 'paradisosolutions_com']

        # Allow user to select a competitor
        competitor_name = st.selectbox("Select a competitor", competitors)

        # Replace with your database query
        query = f"SELECT change_date, COUNT(*) as changes FROM content_changes_temp WHERE competitor_name = '{competitor_name}' GROUP BY change_date ORDER BY change_date"

        # Fetch data from the database
        df = fetch_data(conn, query)

        # Add custom CSS style
        create_css_style()

        # Display the graph
        if not df.empty:
            display_contribution_graph(df)
        else:
            st.write("No changes found.")
    else:
        st.error("Failed to connect to the database.")

if __name__ == "__main__":
    main()