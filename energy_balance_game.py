import streamlit as st
import pandas as pd
import plotly.express as px
import random
import numpy as np

# Load secrets
random_mode = st.secrets["random_mode"]["mode"]
fixed_country = st.secrets["fixed_country"]["name"]

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
    st.session_state.selected_country = random.choice(countries) if random_mode else fixed_country
if 'correct' not in st.session_state:
    st.session_state.correct = False
if 'answers' not in st.session_state:
    st.session_state.answers = []

# Title and description
st.title("Energy Balance Guessing Game")
st.markdown("""
Welcome to the Energy Balance Guessing Game! This game is based on the **World Energy Balances 2023 Highlights** from the International Energy Agency (IEA).

---

### About the Data
The World Energy Balances online data service contains energy balances for 156 countries and 35 regional aggregates. The figures are expressed in thousand tonnes of oil equivalent (ktoe) and in terajoules. Conversion factors used to calculate energy balances and indicators (including GDP, population, industrial production index and ratios calculated with the energy data) are also provided. The database includes transparent notes on methodologies and sources for country-level data. In general, the data are available from 1971 (1960 for OECD countries) to 2021. Preliminary 2022 data are available for select countries, products, and flows. This service is updated twice a year with progressively broader geographical coverage: in April and July, the final edition with global data for year-2.

Note: This game is based on the IEA family countries, which include members, accession, and association countries.

Source: [IEA World Energy Balances](https://www.iea.org/data-and-statistics/data-product/world-energy-balances#energy-balances)

---

### How to Play
1. Each day, a specific country's energy balance data will be selected. Analyze the treemap and the total value of all products for clues about the country's energy balance.
2. You have 5 attempts to guess the country correctly.
3. Enter your guess in the dropdown menu and click "Submit Guess".
4. If your guess is incorrect, the game will show you the difference in shares between your guess and the correct country using a bar chart. The default flow is "Production (PJ)" and differences should also apply to the "Total Final Consumption (PJ)" values.
5. The bar chart displays the percentage difference for each product, helping you refine your next guess.
6. Your previous guesses will be shown on the sidebar, color-coded based on their accuracy: 
   - Green for close (average share difference < 5%)
   - Yellow for moderate (average share difference between 5% and 15%)
   - Red for far (average share difference > 15%)
7. The game ends when you guess the correct country or use all 5 attempts. Good luck!

---

Developed by [Darlain Edeme](https://www.linkedin.com/in/darlain-edeme/)

---
""")

# Set default flow
default_flow = "Production (PJ)"
flows = np.append(flows, "Total Final Consumption (PJ)")

# Flow selection dropdown
selected_flow = st.selectbox("Select a Flow to investigate:", flows, index=list(flows).index(default_flow))

# Filter data by the selected flow
filtered_data = energy_data[energy_data['Flow'] == selected_flow]

# Selected country and filtering data
selected_country = st.session_state.selected_country
country_data = filtered_data[filtered_data['Country'] == selected_country]

# Display total value for the country
total_value = country_data['2021'].sum()
st.subheader(f"Total value for all products: {round(total_value, 2)} PJ")

st.markdown("""
### Energy Balance Treemap
The treemap below shows the energy balance for the selected flow. Each rectangle represents a product, sized proportionally to its total value. The percentage share of each product is also displayed. Use this visualization to analyze the energy profile of the selected country.
""")

# Define a color palette similar to IEA World Energy Outlook
color_palette = px.colors.qualitative.Set1

# Display the treemap with percentage shares
country_data['Percentage'] = (country_data['2021'] / total_value * 100).round(2)
fig = px.treemap(country_data, path=['Product'], values='2021', title=f"Energy Balance",
                 color='Product', color_discrete_sequence=color_palette,
                 custom_data=['Percentage'])
fig.update_traces(texttemplate='%{label}<br>%{customdata[0]}%')
st.plotly_chart(fig)

# Separator
st.markdown('---')

# Guessing section
st.write(f"Round {st.session_state.round + 1} of 5")
guess = st.selectbox("Guess the Country:", countries)
if st.button("Submit Guess"):
    st.session_state.round += 1
    if guess == selected_country:
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
        
        st.markdown("""
        The bar chart below shows the percentage difference for each product between your guessed country and the correct country. This will help you understand how close your guess was and refine your next guess.
        """)

        # Display horizontal bar chart with differences sorted by absolute difference
        distance_data = pd.DataFrame({
            'Product': guessed_country_data.index,
            'Difference (%)': share_difference
        }).reset_index(drop=True).sort_values(by='Difference (%)', ascending=False, key=abs)
        
        fig_distance = px.bar(distance_data, y='Product', x='Difference (%)', title="Difference per Product (%)",
                              color='Product', color_discrete_sequence=color_palette, orientation='h')
        fig_distance.update_layout(xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig_distance)
        st.write(f"Average share difference: {distance:.2f}%")

    if st.session_state.round == 5 or st.session_state.correct:
        if st.session_state.correct:
            st.success(f"Congratulations! You guessed the correct country: {selected_country}")
        else:
            st.error(f"Game Over! The correct country was: {selected_country}")
            st.write("Your guesses and distances were:")
            st.table(pd.DataFrame(st.session_state.answers))
        
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
            result_text = f"Here's my results in today #energywordle: {len(st.session_state.answers)}/5\n{score} https://energywordle.streamlit.app/"
        else:
            result_text = f"I failed today's #energywordle. The correct country was {selected_country}.\n{score} https://energywordle.streamlit.app/"
        
        st.markdown("**Share your score:**")
        st.text_area("", result_text, height=100)

        # Reset the game
        st.session_state.round = 0
        st.session_state.selected_country = random.choice(countries) if random_mode else fixed_country
        st.session_state.correct = False
        st.session_state.answers = []

# Separator
st.markdown('---')

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

st.sidebar.markdown('---')
st.sidebar.markdown("Developed by [D
