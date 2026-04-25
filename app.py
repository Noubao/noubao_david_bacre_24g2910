import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import timedelta, date

# ------------------------------------------------------------------------------
# Configuration de la page
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="CityPulse - Mobilité & Qualité de l'Air",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------------------
# Génération de données factices complexes (Cache pour optimisation)
# ------------------------------------------------------------------------------
@st.cache_data
def load_data():
    """Génère un dataset réaliste sur 365 jours pour 3 grandes villes."""
    np.random.seed(42)
    cities = ['Paris', 'New York', 'Tokyo']
    transports = ['Métro', 'Bus', 'Vélo (Libre-service)', 'Voiture']
    
    start_date = date(2023, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(365)]
    
    data = []
    for city in cities:
        for transport in transports:
            for d in dates:
                # Modulations basiques pour plus de réalisme
                # Moins de vélos en hiver (janvier-mars, déc)
                is_winter = d.month in [1, 2, 3, 11, 12]
                
                # Base passengers
                if transport == 'Métro':
                    base_pass = np.random.randint(50000, 150000)
                    co2_factor = 0.05
                elif transport == 'Bus':
                    base_pass = np.random.randint(20000, 80000)
                    co2_factor = 0.15
                elif transport == 'Vélo (Libre-service)':
                    base_pass = np.random.randint(2000, 15000) if not is_winter else np.random.randint(500, 5000)
                    co2_factor = 0.0
                else: # Voiture
                    base_pass = np.random.randint(100000, 300000)
                    co2_factor = 0.4
                    
                # Variations selon le jour de la semaine (M-F = +)
                if d.weekday() >= 5: # Weekend
                    passengers = int(base_pass * 0.6)
                else:
                    passengers = int(base_pass * 1.2)
                    
                # AQI (Air Quality Index) - corrélé en partie au nombre de voitures
                base_aqi = np.random.randint(30, 80)
                if transport == 'Voiture':
                    aqi = base_aqi + int(passengers / 5000)
                else:
                    aqi = base_aqi
                    
                co2_emissions = passengers * co2_factor
                
                data.append([d, city, transport, passengers, min(aqi, 300), round(co2_emissions, 2)])
                
    df = pd.DataFrame(data, columns=['Date', 'Ville', 'Mode de transport', 'Passagers', 'IQA', 'Emissions CO2 (T)'])
    df['Date'] = pd.to_datetime(df['Date'])
    return df

# ------------------------------------------------------------------------------
# Sidebar et Chargement des données
# ------------------------------------------------------------------------------
st.sidebar.title("🌍 CityPulse")

# Initialisation du paramètre d'état global pour conserver les données (saisie manuelle ou import)
if 'df' not in st.session_state:
    st.session_state.df = load_data()

st.sidebar.markdown("### 📥 Collecte des données")

with st.sidebar.expander("ℹ️ Format du CSV attendu", expanded=False):
    st.markdown("""
    Votre fichier doit contenir ces colonnes exactes :
    - `Date` : AAAA-MM-JJ (ex: 2023-01-15)
    - `Ville` : Texte (ex: Paris)
    - `Mode de transport` : Texte (ex: Bus)
    - `Passagers` : Nombre entier
    - `IQA` : Nombre entier (ex: 45)
    - `Emissions CO2 (T)` : Nombre fractionnaire
    """)

with st.sidebar.expander("📁 Importer un fichier CSV", expanded=False):
    st.markdown("*Note : Déposez ('Drag and drop') votre fichier ci-dessous.*")
    uploaded_file = st.file_uploader("Fichier", type=['csv'], label_visibility="collapsed")

    if uploaded_file is not None:
        try:
            new_df = pd.read_csv(uploaded_file)
            new_df['Date'] = pd.to_datetime(new_df['Date'])
            st.session_state.df = new_df
            st.success("Données personnelles chargées !")
        except Exception as e:
            st.error("Erreur de format. Vérifiez les colonnes.")

with st.sidebar.expander("✍️ Ajouter une donnée manuellement", expanded=False):
    with st.form("form_saisie"):
        f_date = st.date_input("Date")
        f_ville = st.text_input("Ville", value="Paris")
        f_transport = st.selectbox("Mode de transport", ["Métro", "Bus", "Vélo (Libre-service)", "Voiture", "Tramway"])
        f_passagers = st.number_input("Passagers", min_value=0, value=1000, step=100)
        f_iqa = st.number_input("IQA (Qualité de l'air)", min_value=0, max_value=500, value=50, step=1)
        f_co2 = st.number_input("Émissions CO2 (en Tonnes)", min_value=0.0, value=0.0, step=0.1)
        
        submit_btn = st.form_submit_button("Sauvegarder")
        
        if submit_btn:
            new_row = pd.DataFrame([{
                'Date': pd.to_datetime(f_date),
                'Ville': f_ville,
                'Mode de transport': f_transport,
                'Passagers': f_passagers,
                'IQA': f_iqa,
                'Emissions CO2 (T)': f_co2
            }])
            # Ajout à la base de données virtuelle (Session State)
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.success("Donnée ajoutée !")

# Récupérer les données pour l'analyse
df = st.session_state.df

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Filtres d'Analyse")

selected_city = st.sidebar.multiselect(
    "Sélectionnez une ou plusieurs villes :",
    options=df['Ville'].unique(),
    default=df['Ville'].unique()
)

min_date = df['Date'].min().date()
max_date = df['Date'].max().date()
date_range = st.sidebar.date_input(
    "Période d'analyse :",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0]

selected_transports = st.sidebar.multiselect(

    "Modes de transport :",
    options=df['Mode de transport'].unique(),
    default=df['Mode de transport'].unique()
)

# Filtrer le dataframe
mask = (
    df['Ville'].isin(selected_city) &
    (df['Date'].dt.date >= start_date) &
    (df['Date'].dt.date <= end_date) &
    (df['Mode de transport'].isin(selected_transports))
)
filtered_df = df.loc[mask]

# ------------------------------------------------------------------------------
# Main Page - Header et KPIs
# ------------------------------------------------------------------------------
st.title("📊 Tableau de Bord : Mobilité & Environnement")
st.markdown("Analysez les tendances de déplacement et l'impact carbone des villes intelligentes.")

# KPIs
if filtered_df.empty:
    st.warning("Aucune donnée disponible pour vos critères de recherche.")
else:
    col1, col2, col3, col4 = st.columns(4)
    
    total_passagers = filtered_df['Passagers'].sum()
    total_co2 = filtered_df['Emissions CO2 (T)'].sum()
    avg_aqi = filtered_df['IQA'].mean()
    
    col1.metric("Volume de Passagers (Total)", f"{total_passagers:,.0f}".replace(",", " "))
    col2.metric("Émissions CO2 (Total en T)", f"{total_co2:,.0f}".replace(",", " "))
    col3.metric("IQA Moyen (Air Quality)", f"{avg_aqi:.1f}", delta="-2%" if avg_aqi < 60 else "+5%", delta_color="inverse")
    col4.metric("Modes de transport actifs", len(selected_transports))

    st.markdown("---")

    # ------------------------------------------------------------------------------
    # Ligne 1 : Les graphiques temporels
    # ------------------------------------------------------------------------------
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📈 Évolution du volume de voyageurs")
        # Grouper par date et mode
        df_time = filtered_df.groupby(['Date', 'Mode de transport'])['Passagers'].sum().reset_index()
        fig_time = px.line(
            df_time, x='Date', y='Passagers', color='Mode de transport',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_time.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_time, use_container_width=True)

    with col_chart2:
        st.subheader("🌫️ Corrélation: Passagers vs Qualité de l'Air")
        # Grouper par Ville et Date pour l'IQA moyen
        df_scatter = filtered_df.groupby('Date').agg({'Passagers': 'sum', 'IQA': 'mean'}).reset_index()
        fig_scatter = px.scatter(
            df_scatter, x='Passagers', y='IQA',
            color='IQA', color_continuous_scale="Viridis"
        )
        fig_scatter.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_scatter, use_container_width=True)

    # ------------------------------------------------------------------------------
    # Ligne 2 : Analyse globale et détails
    # ------------------------------------------------------------------------------
    st.markdown("---")
    col_chart3, col_chart4 = st.columns([1, 2])
    
    with col_chart3:
        st.subheader("🚙 Répartition Modale")
        df_pie = filtered_df.groupby('Mode de transport')['Passagers'].sum().reset_index()
        fig_pie = px.pie(
            df_pie, values='Passagers', names='Mode de transport',
            hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart4:
        st.subheader("🏢 Émissions CO2 par Ville")
        df_bar = filtered_df.groupby(['Ville', 'Mode de transport'])['Emissions CO2 (T)'].sum().reset_index()
        fig_bar = px.bar(
            df_bar, x='Ville', y='Emissions CO2 (T)', color='Mode de transport', barmode='stack',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True)
