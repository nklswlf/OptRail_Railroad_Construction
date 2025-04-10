import streamlit as st
from streamlit_function import *

# Titel der App
st.title("Auswertung Bahnlogistik OptRail")

# Tabs erstellen
tabs = st.tabs(["🗺️ Instanz","🚄 Lösung 1", "🚧 Lösung 2", "🚦 Lösung 3", "🚂 Lösung 4", "🚜 Lösung 5", "📊 Vergleich"])

with tabs[0]:
    upload_instance, instance_data, instance = upload_instance()

# Inhalt von Tab 1
with tabs[1]:
    uploaded_solution, solution_data, instance = upload_solution(1)
    results_1 = streamlit(1, uploaded_solution, solution_data)


# Inhalt von Tab 2
with tabs[2]:
    uploaded_solution, solution_data, filler = upload_solution(2, instance)
    results_2 = streamlit(2, uploaded_solution, solution_data)


# Inhalt von Tab 3
with tabs[3]:
    uploaded_solution, solution_data, filler = upload_solution(3, instance)
    results_3 = streamlit(3, uploaded_solution, solution_data)

with tabs[4]:
    uploaded_solution, solution_data, filler = upload_solution(4, instance)
    results_4 = streamlit(4, uploaded_solution, solution_data)

with tabs[5]:
    uploaded_solution, solution_data, filler = upload_solution(5, instance)
    results_5 = streamlit(5, uploaded_solution, solution_data)

with tabs[6]:
    compare_results(results_1, results_2, results_3, results_4, results_5)