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
if 'final_flow' not in st.session_state:
    st.session_state.final_flow = "Production (PJ)"  # Default flow for final charts

# Title and description
st.title("Weekly Energy Balance Guessing Game")

with st.expander("About the Data", expanded=True):
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
tfc_data = energy_data[energy_data['Flow'] == "Total final consumption (PJ)"]

# Selected country and filtering data
selected_country = st.session_state.selected_country
country_data = filtered_data[filtered_data['Country'] == selected_country]
tfc_country_data = tfc_data[tfc_data['Country'] == selected_country]

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

# Guessing section
st.write(f"Round {st.session_state.round + 1} of 5")
guess = st.selectbox("Guess the Country:", [country for country in countries if country not in [answer['guess'] for answer in st.session_state.answers]])
if st.button("Submit Guess"):
    st.session_state.round += 1
    if guess == selected_country:
        st.session_state.correct = True
    else:
        guessed_country_data = tfc_data[tfc_data['Country'] == guess]
        guessed_country_data = guessed_country_data.set_index('Product').reindex(tfc_country_data['Product']).fillna(0)
        guessed_country_data['2021'] = guessed_country_data['2021'].replace(np.nan, 0)
        tfc_country_data = tfc_country_data.set_index('Product').reindex(guessed_country_data.index).fillna(0)
        
        guessed_share = guessed_country_data['2021'] / guessed_country_data['2021'].sum()
        correct_share = tfc_country_data['2021'] / tfc_country_data['2021'].sum()
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
                              color='Product', color_discrete_map=color_palette, orientation='h')
        fig_distance.update_layout(xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig_distance)
        st.write(f"Average share difference: {distance:.2f}%")

        # Generate explanations for each product
        explanations = []
        for _, row in distance_data.iterrows():
            product = row['Product']
            diff = row['Difference (%)']
            if diff != 0:
                if diff > 0:
                    explanation = f"The country you selected has a share of **{product}** in TFC that is **{abs(diff):.2f}% higher** than the target country."
                else:
                    explanation = f"The country you selected has a share of **{product}** in TFC that is **{abs(diff):.2f}% lower** than the target country."
                explanations.append((diff, explanation, product))

        # Sort explanations by absolute difference in descending order
        explanations.sort(key=lambda x: abs(x[0]), reverse=True)

        with st.expander("Detailed Differences", expanded=False):
            for _, explanation, product in explanations:
                product_color = color_palette[product]
                st.markdown(f"<span style='color:{product_color}'>{explanation}</span>", unsafe_allow_html=True)

    if st.session_state.round == 5 or st.session_state.correct:
        attempts = st.session_state.round if st.session_state.correct else 5
        if st.session_state.correct:
            st.success(f"Congratulations! You guessed the correct country: {selected_country}")
        else:
            st.error(f"Game Over! The correct country was: {selected_country}")
            st.write("Your guesses and distances were:")
            st.table(pd.DataFrame(st.session_state.answers))

        # Provide links to learn more about the countries involved in the game
        countries_involved = [selected_country] + [answer['guess'] for answer in reversed(st.session_state.answers)]
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
            result_text = f"Here's my results in today #energywordle: {attempts}/5\n{score} https://energywordle.streamlit.app/"
        else:
            result_text = f"I failed at today's energy wordle, can you make it?\n{score} https://energywordle.streamlit.app/"
        
        st.markdown("**Share your score:**")
        st.text_area("", result_text, height=100)

        # Dropdown menu to select flow for final charts
        selected_flow_final = st.selectbox("Select a Flow for final charts:", flows, index=list(flows).index(st.session_state.final_flow), key='final_flow')

        # Prevent page refresh on final chart flow selection
        st.session_state.final_flow = selected_flow_final
        
        final_filtered_data = energy_data[energy_data['Flow'] == st.session_state.final_flow]

        # Prepare data for final charts
        final_chart_data = final_filtered_data[final_filtered_data['Country'].isin(countries_involved)]
        final_chart_data['Country'] = pd.Categorical(final_chart_data['Country'], categories=countries_involved, ordered=True)

        # Stacked bar chart for total values
        fig_stacked = px.bar(final_chart_data, x='Country', y='2021', color='Product', title="Total Values by Country",
                             color_discrete_map=color_palette)
        st.plotly_chart(fig_stacked)

        # Stacked 100% bar chart for relative shares
        final_chart_data['Percentage'] = final_chart_data.groupby('Country')['2021'].transform(lambda x: x / x.sum() * 100)
        fig_stacked_100 = px.bar(final_chart_data, x='Country', y='Percentage', color='Product', title="Relative Shares by Country",
                                 color_discrete_map=color_palette)
        st.plotly_chart(fig_stacked_100)

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
        sidebar_text = f"<span style='color:{color}'>{answer['guess']}: {distance:.2f}%"
        sidebar_text += "</span>"
        st.sidebar.markdown(sidebar_text, unsafe_allow_html=True)

st.sidebar.markdown('---')
st.sidebar.markdown("Developed by [Darlain Edeme](https://www.linkedin.com/in/darlain-edeme/)")
