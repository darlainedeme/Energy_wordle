import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random
import numpy as np

# Load the CSV file
file_path = 'WorldEnergyBalancesHighlights2023.csv'
energy_data = pd.read_csv(file_path)

# Convert the '2021' column to numeric, errors='coerce' will replace non-convertible values with NaN
energy_data['2021'] = pd.to_numeric(energy_data['2021'], errors='coerce')

# Extract unique flows and countries
flows = energy_data['Flow'].unique()
countries = sorted(energy_data['Country'].unique())

# Initialize session state
if 'round' not in st.session_state:
    st.session_state.round = 0
if 'selected_country' not in st.session_state:
    st.session_state.selected_country = random.choice(countries)
if 'correct' not in st.session_state:
    st.session_state.correct = False
if 'answers' not in st.session_state:
    st.session_state.answers = []

# Title
st.title("Energy Balance Guessing Game")

# Flow selection dropdown
selected_flow = st.selectbox("Select a Flow to investigate:", flows)

# Filter data by the selected flow
filtered_data = energy_data[energy_data['Flow'] == selected_flow]

# Random country selection and filtering data
random_country = st.session_state.selected_country
country_data = filtered_data[filtered_data['Country'] == random_country]

# Display total value for the country
total_value = country_data['2021'].sum()
st.subheader(f"Total value for all products: {round(total_value, 2)} PJ")

# Define a color palette similar to IEA World Energy Outlook
color_palette = px.colors.qualitative.Set1

# Display the treemap with percentage shares
country_data['Percentage'] = (country_data['2021'] / total_value * 100).round(2)
fig = px.treemap(country_data, path=['Product'], values='2021', title=f"Energy Balance",
                 color='Product', color_discrete_sequence=color_palette,
                 custom_data=['Percentage'])
fig.update_traces(texttemplate='%{label}<br>%{customdata[0]}%')
st.plotly_chart(fig)

# Guessing section
st.write(f"Round {st.session_state.round + 1} of 5")
guess = st.selectbox("Guess the Country:", countries)
if st.button("Submit Guess"):
    st.session_state.round += 1
    if guess == random_country:
        st.session_state.correct = True
    else:
        guessed_country_data = filtered_data[filtered_data['Country'] == guess]
        guessed_country_data = guessed_country_data.set_index('Product').reindex(country_data['Product']).fillna(0)
        guessed_country_data['2021'] = guessed_country_data['2021'].replace(np.nan, 0)
        country_data = country_data.set_index('Product').reindex(guessed_country_data.index).fillna(0)
        
        guessed_share = guessed_country_data['2021'] / guessed_country_data['2021'].sum()
        correct_share = country_data['2021'] / country_data['2021'].sum()
        share_difference = (guessed_share - correct_share) * 100
        
        distance = share_difference.abs().mean()
        st.session_state.answers.append({
            'guess': guess,
            'distance': distance
        })
        
        st.write("Incorrect Guess!")
        st.write(f"Shares for {guess} vs Correct Shares:")
        
        # Display horizontal bar chart with differences
        distance_data = pd.DataFrame({
            'Product': guessed_country_data.index,
            'Difference (%)': share_difference
        }).reset_index(drop=True)
        
        fig_distance = px.bar(distance_data, y='Product', x='Difference (%)', title="Difference per Product",
                              color='Product', color_discrete_sequence=color_palette, orientation='h')
        fig_distance.update_layout(xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig_distance)
        st.write(f"Average share difference: {distance:.2f}%")

    if st.session_state.round == 5 or st.session_state.correct:
        if st.session_state.correct:
            st.success(f"Congratulations! You guessed the correct country: {random_country}")
        else:
            st.error(f"Game Over! The correct country was: {random_country}")
            st.write("Your guesses and distances were:")
            st.table(pd.DataFrame(st.session_state.answers))
        st.session_state.round = 0
        st.session_state.selected_country = random.choice(countries)
        st.session_state.correct = False
        st.session_state.answers = []

# Sidebar to display guessed countries and distances with colors
st.sidebar.header("Guessed Countries and Distances")
if st.session_state.answers:
    for answer in st.session_state.answers:
        distance = answer['distance']
        if distance < 5:
            color = 'green'
        elif distance < 15:
            color = 'yellow'
        else:
            color = 'red'
        st.sidebar.markdown(f"<span style='color:{color}'>{answer['guess']}: {distance:.2f}%</span>", unsafe_allow_html=True)
