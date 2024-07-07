import streamlit as st
import pandas as pd
import plotly.express as px
import random
import numpy as np
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# CSS to scale the app content
st.markdown(
    """
    <style>
    body {
        zoom: 1; /* Adjust the zoom level as needed */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Load secrets
smtp_user = st.secrets["smtp_user"]
smtp_password = st.secrets["smtp_password"]

# Load game mode
random_mode = st.secrets["random_mode"]
fixed_country = st.secrets["fixed_country"]

def send_email(to_emails, subject, content):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    # Create the message
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    if isinstance(to_emails, list):
        msg['To'] = ', '.join(to_emails)
    else:
        msg['To'] = to_emails
    msg['Subject'] = subject

    # Attach the content
    msg.attach(MIMEText(content, 'plain'))

    # Send the email
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_user, smtp_password)
    server.send_message(msg)
    server.quit()

# Load the CSV file
file_path = 'WorldEnergyBalancesHighlights2023.csv'
energy_data = pd.read_csv(file_path)

# Convert the '2021' column to numeric, errors='coerce' will replace non-convertible values with NaN
energy_data['2021'] = pd.to_numeric(energy_data['2021'], errors='coerce')

# Extract unique flows and countries
flows = energy_data['Flow'].unique()
countries = sorted(energy_data['Country'].unique())

if 'username' not in st.session_state:
    st.session_state.username = ""
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.now()
if 'end_time' not in st.session_state:
    st.session_state.end_time = None
if 'round' not in st.session_state:
    st.session_state.round = 0
if 'selected_country' not in st.session_state:
    st.session_state.selected_country = random.choice(countries) if random_mode else fixed_country
if 'correct' not in st.session_state:
    st.session_state.correct = False
if 'answers' not in st.session_state:
    st.session_state.answers = []
if 'final_flow' not in st.session_state:
    st.session_state.final_flow = "Production (PJ)"  # Default flow for final charts

# Function to reset the game state
def reset_game():
    st.session_state.round = 0
    st.session_state.selected_country = random.choice(countries) if random_mode else fixed_country
    st.session_state.correct = False
    st.session_state.answers = []
    st.session_state.start_time = None
    st.session_state.end_time = None


# Function to handle the email sending
def send_game_summary():
    username = st.session_state.username
    start_time = st.session_state.start_time
    end_time = st.session_state.end_time
    delta_seconds = round((end_time - start_time).total_seconds() if start_time and end_time else "Unknown")
    answers = st.session_state.answers
    selected_country = st.session_state.selected_country
    
    summary = f"Player: {username}\n"
    summary += f"Game duration: {delta_seconds} seconds\n"
    summary += "Results:\n"
    for answer in answers:
        summary += f"Round {answers.index(answer) + 1}: {answer['guess']}\n"
    summary += f"Correct Country: {selected_country}\n"
    
    send_email([smtp_user], "Energy Wordle Game Summary", summary)

# Main game page
def main_game():
    if not st.session_state.username:
        st.session_state.username = st.text_input("Enter your username to start the game:")
        if st.button("Start Game"):
            if st.session_state.username:
                st.session_state.start_time = datetime.now()
                st.experimental_rerun()
            else:
                st.error("Please enter a username to start the game.")
    else:
        st.title("Weekly Energy Balance Guessing Game")

        with st.expander("About the Data", expanded=False):
            st.markdown("""
            The World Energy Balances online data service contains energy balances for 156 countries and 35 regional aggregates. 
            The figures are expressed in thousand tonnes of oil equivalent (ktoe) and in terajoules. Conversion factors used to calculate energy balances and indicators 
            (including GDP, population, industrial production index and ratios calculated with the energy data) are also provided. The database includes transparent notes 
            on methodologies and sources for country-level data. In general, the data are available from 1971 (1960 for OECD countries) to 2021. Preliminary 2022 data are 
            available for select countries, products, and flows. This service is updated twice a year with progressively broader geographical coverage: in April and July, 
            the final edition with global data for year-2.

            Note: This game is based on the IEA family countries, which include members, accession, and association countries.

            Source: [IEA World Energy Balances](https://www.iea.org/data-and-statistics/data-product/world-energy-balances#energy-balances)
            """)

        with st.expander("How to Play", expanded=True):
            st.markdown("""
            ### How to Play
            1. Each week, a specific country's energy mix data will be selected. Analyze the treemap and the total value of all products for clues about the country's energy mix.
            2. You have 5 attempts to guess the country correctly.
            3. Enter your guess in the dropdown menu and click "Submit Guess".
            4. If your guess is incorrect, the game will show you the difference in shares between your guess and the correct country using a bar chart. The default flow is "Production (PJ)" and differences should also apply to the "Total Final Consumption (PJ)" values.
            5. The bar chart displays the percentage difference for each product, helping you refine your next guess.
            6. Your previous guesses will be shown on the sidebar, color-coded based on their accuracy: 
               - Green for close (average share difference < 5%)
               - Yellow for moderate (average share difference between 5% and 15%)
               - Red for far (average share difference > 15%)
            7. The game ends when you guess the correct country or use all 5 attempts. Good luck!
            """)

        # Set default flow
        default_flow = "Production (PJ)"

        st.markdown("""
        ### Energy Mix Treemap
        The treemap below shows the energy mix for the selected flow. Each rectangle represents a product, sized proportionally to its total value. The percentage share of each product is also displayed. Use this visualization to analyze the energy profile of the selected country.
        """)

        # Flow selection dropdown
        selected_flow = st.selectbox("Select a Flow to investigate:", flows, index=list(flows).index(default_flow))

        # Determine the unit of measure based on the selected flow
        if selected_flow == "Electricity output (GWh)":
            unit_of_measure = "GWh"
        else:
            unit_of_measure = "PJ"

        # Filter data by the selected flow
        filtered_data = energy_data[energy_data['Flow'] == selected_flow]

        # Filter data for total final consumption only
        filter_data = energy_data[energy_data['Flow'] == "Production (PJ)"]

        # Selected country and filtering data
        selected_country = st.session_state.selected_country
        country_data = filtered_data[filtered_data['Country'] == selected_country]
        filter_country_data = filter_data[filter_data['Country'] == selected_country]

        # Define the color palette
        color_palette = {
            "Coal, peat and oil shale": "#4B5320",
            "Crude, NGL and feedstocks": "#A52A2A",
            "Oil products": "#FF8C00",
            "Natural gas": "#1E90FF",
            "Nuclear": "#FFD700",
            "Renewables and waste": "#32CD32",
            "Electricity": "#9400D3",
            "Heat": "#FF4500",
            "Fossil fuels": "#708090",
            "Renewable sources": "#00FA9A"
        }

        # Display total value for the country
        total_value = int(country_data['2021'].sum())

        # Display the treemap with percentage shares
        country_data['Percentage'] = (country_data['2021'] / total_value * 100).round(1)
        fig = px.treemap(country_data, path=['Product'], values='2021', title=f"Energy Mix: (Total value for all products: {total_value} {unit_of_measure})",
                         color='Product', color_discrete_map=color_palette,
                         custom_data=['Percentage'])
        fig.update_traces(texttemplate='%{label}<br>%{value:.1f}<br>%{customdata[0]}%', hovertemplate=None)
        fig.update_layout(height=600, width=800)
        st.plotly_chart(fig)

        # Separator
        st.markdown('---')

        if st.session_state.round < 5 and not st.session_state.correct:
            # Guessing section
            st.write(f"Round {st.session_state.round + 1} of 5")
            guess = st.selectbox("Guess the Country:", [country for country in countries])
            if st.button("Submit Guess"):
                st.session_state.round += 1
                if guess == selected_country:
                    st.session_state.correct = True
                else:
                    guessed_country_data = filter_data[filter_data['Country'] == guess]
                    guessed_country_data = guessed_country_data.set_index('Product').reindex(filter_country_data['Product']).fillna(0)
                    guessed_country_data['2021'] = guessed_country_data['2021'].replace(np.nan, 0)
                    filter_country_data = filter_country_data.set_index('Product').reindex(guessed_country_data.index).fillna(0)

                    guessed_share = guessed_country_data['2021'] / guessed_country_data['2021'].sum()
                    correct_share = filter_country_data['2021'] / filter_country_data['2021'].sum()
                    share_difference = (guessed_share - correct_share) * 100

                    distance = share_difference.abs().mean()
                    st.session_state.answers.append({
                        'guess': guess,
                        'distance': distance
                    })

                    st.write("Incorrect Guess!")
                    st.write(f"Shares for {guess} vs Correct Shares:")

                    st.markdown("""
                    The bar chart below shows the production percentage difference for each product between your guessed country and the correct country. This will help you understand how close your guess was and refine your next guess.
                    """)

                    # Display horizontal bar chart with differences sorted by absolute difference
                    distance_data = pd.DataFrame({
                        'Product': guessed_country_data.index,
                        'Difference (%)': share_difference
                    }).reset_index(drop=True).sort_values(by='Difference (%)', ascending=False, key=abs)

                    fig_distance = px.bar(distance_data, y='Product', x='Difference (%)', title="Difference per Product (%)",
                                          color='Product', color_discrete_map=color_palette, orientation='h')
                    fig_distance.update_layout(xaxis_title=None, yaxis_title=None)
                    st.plotly_chart(fig_distance)

                    # Generate explanations for each product
                    explanations = []
                    for _, row in distance_data.iterrows():
                        product = row['Product']
                        diff = row['Difference (%)']
                        guessed_country_name = guess  # Use the actual guessed country name
                        if diff != 0:
                            if diff > 0:
                                explanation = f"{guessed_country_name} has a share of **{product}** in production that is **{abs(diff):.2f}% higher** than the target country."
                                if abs(diff) < 5:
                                    explanation += " You were very close, you're on the right track with this product's share."
                                elif 5 <= abs(diff) < 15:
                                    explanation += " You are looking for a country that produces slightly less of this product (as a share)."
                                elif 15 <= abs(diff) < 30:
                                    explanation += " You are looking for a country that produces less of this product (as a share)."
                                else:
                                    explanation += " You are looking for a country that produces much less of this product (as a share)."
                            else:
                                explanation = f"{guessed_country_name} has a share of **{product}** in production that is **{abs(diff):.2f}% lower** than the target country."
                                if abs(diff) < 5:
                                    explanation += " You were very close, you're on the right track with this product's share."
                                elif 5 <= abs(diff) < 15:
                                    explanation += " You are looking for a country that produces slightly more of this product (as a share)."
                                elif 15 <= abs(diff) < 30:
                                    explanation += " You are looking for a country that produces more of this product (as a share)."
                                else:
                                    explanation += " You are looking for a country that produces much more of this product (as a share)."
                            explanations.append((diff, explanation, product))

                    # Sort explanations by absolute difference in descending order
                    explanations.sort(key=lambda x: abs(x[0]), reverse=True)

                    with st.expander("Detailed Differences", expanded=False):
                        for _, explanation, product in explanations:
                            product_color = color_palette[product]
                            st.markdown(f"<span style='color:{product_color}'>{explanation}</span>", unsafe_allow_html=True)

        if st.session_state.round == 5 or st.session_state.correct:
            if st.session_state.correct:
                st.success(f"Congratulations! You guessed the correct country: {selected_country}")
            else:
                st.error(f"Game Over! The correct country was: {selected_country}")

            st.markdown("Want to explore the results? Click on the top left 'Explore the Results'.")
            
            # Record end time
            st.session_state.end_time = datetime.now()

            # Provide links to learn more about the countries involved in the game
            countries_involved = [selected_country] + [answer['guess'] for answer in reversed(st.session_state.answers) if answer['guess'] != selected_country]
            countries_involved = list(set(countries_involved))
            country_links = []
            for country in countries_involved:
                country_url = country.lower().replace(" ", "-")
                if "turkiye" in country_url:
                    country_url = "turkiye"
                elif "china" in country_url:
                    country_url = "china"
                country_links.append(f"[{country}](https://www.iea.org/countries/{country_url})")
            st.markdown("### Learn more about these countries' energy sectors:")
            st.markdown(", ".join(country_links))
            
            # Share your score text
            score = ""
            for answer in st.session_state.answers:
                distance = answer['distance']
                if distance < 5:
                    score += "🟩"
                elif distance < 15:
                    score += "🟨"
                else:
                    score += "🟥"

            if st.session_state.correct:
                if st.session_state.round == 1:
                    score = "🟩"
                result_text = f"Here's my results in today #energywordle: {st.session_state.round}/5\n{score} https://energywordle.streamlit.app/"
            else:
                result_text = f"I failed at today's energy wordle, can you make it?\n{score} https://energywordle.streamlit.app/"
            
            st.markdown("**Share your score:**")
            st.text_area("", result_text, height=100)

            st.write("Come back next Tuesday morning for the next match. In the meantime, explore your results.")
            
            # Send game summary email
            send_game_summary()

# Explore results page
def explore_results():
    st.title("Explore the Results")

    # Collect involved countries
    countries_involved = [st.session_state.selected_country] + list(set([answer['guess'] for answer in reversed(st.session_state.answers) if answer['guess'] != st.session_state.selected_country]))

    # Add an empty bar for visual separation
    countries_involved.insert(1, " ")
    
    # Dropdown menu to select flow for final charts
    selected_flow_final = st.selectbox(
        "Select a Flow for final charts:",
        flows,
        index=list(flows).index(st.session_state.final_flow),
        key='final_flow_selectbox'
    )

    final_filtered_data = energy_data[energy_data['Flow'] == selected_flow_final]

    # Get unique products for the selected flow
    unique_products = final_filtered_data['Product'].unique()

    # Prepare data for final charts
    final_chart_data = final_filtered_data[final_filtered_data['Country'].isin(countries_involved)]
    final_chart_data['Country'] = pd.Categorical(final_chart_data['Country'], categories=countries_involved, ordered=True)

    # Reorder the dataframe based on the categorical order
    final_chart_data = final_chart_data.sort_values(by='Country')

    # Add empty rows for each product
    empty_rows = pd.DataFrame({
        "Country": [" "] * len(unique_products),
        "Flow": [selected_flow_final] * len(unique_products),
        "Product": unique_products,
        "2021": [0] * len(unique_products)
    })
    final_chart_data = pd.concat([final_chart_data.iloc[:len(unique_products)], empty_rows, final_chart_data.iloc[len(unique_products):]]).reset_index(drop=True)

    # Define the color palette
    color_palette = {
        "Coal, peat and oil shale": "#4B5320",
        "Crude, NGL and feedstocks": "#A52A2A",
        "Oil products": "#FF8C00",
        "Natural gas": "#1E90FF",
        "Nuclear": "#FFD700",
        "Renewables and waste": "#32CD32",
        "Electricity": "#9400D3",
        "Heat": "#FF4500",
        "Fossil fuels": "#708090",
        "Renewable sources": "#00FA9A"
    }

    # Stacked bar chart for total values
    fig_stacked = px.bar(final_chart_data, x='Country', y='2021', color='Product', title="Total Values by Country",
                         color_discrete_map=color_palette)
    st.plotly_chart(fig_stacked)

    # Stacked 100% bar chart for relative shares
    final_chart_data['Percentage'] = final_chart_data.groupby('Country')['2021'].transform(lambda x: x / x.sum() * 100)
    fig_stacked_100 = px.bar(final_chart_data, x='Country', y='Percentage', color='Product', title="Relative Shares by Country",
                             color_discrete_map=color_palette)
    st.plotly_chart(fig_stacked_100)

    # Provide links to learn more about the countries involved in the game
    country_links = []
    for country in countries_involved:
        if country != " ":
            country_url = country.lower().replace(" ", "-")
            if "turkiye" in country_url:
                country_url = "turkiye"
            elif "china" in country_url:
                country_url = "china"
            country_links.append(f"[{country}](https://www.iea.org/countries/{country_url})")
    st.markdown("### Learn more about these countries' energy sectors:")
    st.markdown(", ".join(country_links))

# Sidebar navigation
nav_option = st.sidebar.radio("Navigation", ["Play Game", "Explore the Results"])

if nav_option == "Explore the Results":
    if st.session_state.round < 5 and not st.session_state.correct:
        st.warning("Go back to the game and once you've finished it, come here to explore the results.")
    else:
        explore_results()
else:
    main_game()

# Sidebar to display guessed countries and distances with colored squares
st.sidebar.header("Guessed Countries and Distances")
if st.session_state.answers:
    for answer in st.session_state.answers:
        distance = answer['distance']
        if distance < 5:
            color = '🟩'
        elif distance < 15:
            color = '🟨'
        else:
            color = '🟥'
        sidebar_text = f"{color} {answer['guess']}"
        st.sidebar.markdown(sidebar_text)

st.sidebar.markdown('---')
st.sidebar.markdown("Developed by [Darlain Edeme](https://www.linkedin.com/in/darlain-edeme/)")
