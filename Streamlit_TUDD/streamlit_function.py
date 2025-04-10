import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import random
import datetime as dt

class SolutionApp:
    def __init__(self):
        self.solution_data = dict()
        self.instance_data = None
        #self.instance_folder = os.path.join(os.path.dirname(__file__), "Instanzen")

    def upload_instance(self):
        uploaded_instance = st.file_uploader("Instanz-Datei hochladen", type=["json"], key="instance_uploader")
        if uploaded_instance:
            self.instance_data = json.load(uploaded_instance)
            st.success("Instanzdatei erfolgreich hochgeladen!")

    def upload_solution(self, key):
        uploaded_solution = st.file_uploader("Lösungsdatei hochladen", type=["json"], key=f"solution_uploader_{key}")
        if uploaded_solution:
            self.solution_data[key] = json.load(uploaded_solution)
            st.success("Lösungsdatei erfolgreich hochgeladen!")
            return True

    def show_worker_gantt(self, current_solution, key):
        # --- Gantt-Diagramm: Arbeiter ---
        st.subheader("Gantt-Diagramm: Arbeiter")
        worker_assignments = current_solution.get("Arbeiterloesung", {}).get("Arbeiterzuweisung", {})
        
        # Daten aufbereiten
        worker_rows = [
            {
                'Arbeiter': worker,
                'Start': shift['Start'],
                'Ende': shift['Ende'],
                'Schichttyp': 'Frühschicht' if pd.to_datetime(shift['Start']).hour < 14 else 'Spätschicht',
                'Baustelle': shift['Auftragsnummer']
            }
            for worker, shifts in worker_assignments.items() for shift in shifts
        ]
        df_worker = pd.DataFrame(worker_rows)
        
        if df_worker.empty:
            st.info("Keine Arbeiterzuweisungen vorhanden.")
        else:
            # Arbeiter sortieren in umgekehrter Reihenfolge
            df_worker['Arbeiter'] = pd.Categorical(
                df_worker['Arbeiter'],
                categories=sorted(df_worker['Arbeiter'].unique(), key=lambda x: int(x.split('_')[1]), reverse=True)
            )
            sorted_workers = sorted(df_worker['Arbeiter'].unique(), key=lambda x: int(x.split('_')[1]), reverse=True)

            # Anzahl verschiedener Baustellen pro Arbeiter zählen
            arbeiter_anzahl_baustellen_dict = (
                df_worker.groupby('Arbeiter', observed=False)['Baustelle']
                .nunique()
                .to_dict()
            )
            arbeiter_anzahl_baustellen_dict = {str(worker.split('_')[1]): sites for worker, sites in arbeiter_anzahl_baustellen_dict.items()}
        
            # Anzahl der Schichten pro Arbeiter und Schichttyp
            arbeiter_schicht_dict = (
                df_worker.groupby(['Arbeiter', 'Schichttyp'], observed=False)
                .size()
                .unstack(fill_value=0)
                .rename_axis(None, axis=1)
                .to_dict(orient='index')
            )
            arbeiter_schicht_dict = {str(worker.split('_')[1]): shifts for worker, shifts in arbeiter_schicht_dict.items()}
        
            # Gantt-Diagramm
            fig_worker = px.timeline(
                df_worker,
                x_start="Start",
                x_end="Ende",
                y="Arbeiter",
                color="Schichttyp",
                title="Arbeiterzuweisungen nach Schichttyp",
                color_discrete_map={"Frühschicht": "lightblue", "Spätschicht": "lightcoral"},
                category_orders={"Arbeiter": sorted_workers}
            )
        
            # Wochenenden hervorheben
            start_date = pd.to_datetime(df_worker['Start']).min().date()
            end_date = pd.to_datetime(df_worker['Ende']).max().date()
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() in [5, 6]:
                    fig_worker.add_vrect(
                        x0=dt.datetime.combine(current_date, dt.datetime.min.time()),
                        x1=dt.datetime.combine(current_date + dt.timedelta(days=1), dt.datetime.min.time()),
                        fillcolor="lightgrey",
                        opacity=0.3,
                        layer="below",
                        line_width=0,
                    )
                current_date += dt.timedelta(days=1)
        
            # Diagramm anzeigen
            st.plotly_chart(fig_worker, key=f"worker_gantt_{key}")

    def show_machine_gantt(self, current_solution, key):
        # --- Gantt-Diagramm: Maschinen ---
        st.subheader("Gantt-Diagramm: Maschinen")
        machine_assignments = current_solution.get("MaschinenLoesung", {}).get("Maschinenzuweisung", {})

        # Daten aufbereiten
        machine_rows = [
            {
                'Maschine': machine,
                'Start': usage['Start'],
                'Ende': usage['Ende'],
                'Baustelle': usage['Auftragsnummer'],
                'Dauer': usage['Dauer']
            }
            for machine, usages in machine_assignments.items() for usage in usages
        ]
        # Auch Anbaugeräte auslesen
        attachment_assignments = current_solution.get("AnbaugeraeteLoesung", {}).get("Anbaugeraetzuweisung", {})
        attachment_rows = [
            {
                'Maschine': attachment,
                'Start': usage['Start'],
                'Ende': usage['Ende'],
                'Baustelle': usage['Auftragsnummer'],
                'Dauer': usage['Dauer']
            }
            for attachment, usages in attachment_assignments.items() for usage in usages
        ]
        df_machine = pd.DataFrame(machine_rows + attachment_rows)


        if df_machine.empty:
            st.info("Keine Maschinenzuweisungen vorhanden.")
            return

        # Stunden in Nutzung
        stunden_in_nutzung_dict = df_machine.groupby('Maschine')['Dauer'].sum().to_dict()
        tage_in_nutzung_dict = {k: v / 24 for k, v in stunden_in_nutzung_dict.items()}
        maschinen_anzahl_baustellen_dict = df_machine.groupby('Maschine')['Baustelle'].nunique().to_dict()

        # Baustellen sortieren
        unique_sites = sorted(df_machine['Baustelle'].unique(), key=lambda x: int(x))
        color_map = {
            site: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
            for i, site in enumerate(unique_sites)
        }

        # Gantt-Diagramm erstellen
        fig_machine = px.timeline(
            df_machine,
            x_start="Start",
            x_end="Ende",
            y="Maschine",
            color="Baustelle",
            title="Maschinen- und Anbaugerätezuweisungen nach Baustelle",
            color_discrete_map=color_map,
            category_orders={
                "Baustelle": unique_sites,
                "Maschine": list(dict.fromkeys([row["Maschine"] for row in machine_rows + attachment_rows]))
            }
        )
        fig_machine.update_yaxes(autorange="reversed") 

        # Wochenenden hervorheben
        start_date = pd.to_datetime(df_machine['Start']).min().date()
        end_date = pd.to_datetime(df_machine['Ende']).max().date()
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() in [5, 6]:
                fig_machine.add_vrect(
                    x0=dt.datetime.combine(current_date, dt.datetime.min.time()),
                    x1=dt.datetime.combine(current_date + dt.timedelta(days=1), dt.datetime.min.time()),
                    fillcolor="lightgrey",
                    opacity=0.3,
                    layer="below",
                    line_width=0,
                )
            current_date += dt.timedelta(days=1)

        # Diagramm anzeigen
        st.plotly_chart(fig_machine, key=f"machine_gantt_{key}")



    def streamlit(self, key):
        current_solution = self.solution_data[key]

        self.show_worker_gantt(current_solution, key)
        self.show_machine_gantt(current_solution, key)
        
    






    def compare_results(self):
        pass


    def run(self):

        selected = False
        if not selected:
            # Anzahl der Lösungen Button
            if "num_solutions" not in st.session_state:
                st.session_state.num_solutions = 2
            if "confirmed_num_solutions" not in st.session_state:
                st.session_state.confirmed_num_solutions = False
            if not st.session_state.confirmed_num_solutions:
                num_selected = st.slider(
                        "Anzahl der Lösungen zum Vergleichen:",
                        min_value=2,
                        max_value=6,
                        value=2,
                        step=1)
                if st.button("Bestätigen"):
                    st.session_state.num_solutions = num_selected
                    st.session_state.confirmed_num_solutions = True
                    st.rerun()
                st.stop()
            # Anzahl der Lösungen Definition
            num_solutions = st.session_state.num_solutions
            selected = True


        # Tabs erstellen
        if "solution_emojis" not in st.session_state:
            emojis = ["🚄", "🛤️", "🚆", "🚇", "🚈", "🚉", "🚋"]
            st.session_state.solution_emojis = random.sample(emojis, st.session_state.num_solutions)

        tab_labels = ["🗺️ Instanz"]
        for i in range(st.session_state.num_solutions):
            tab_labels.append(f"{st.session_state.solution_emojis[i]} Lösung {i + 1}")
        tab_labels.append("📊 Vergleich")
        tabs = st.tabs(tab_labels)

        # Tab 0: Instanz
        with tabs[0]:
            self.upload_instance()

        # Tabs 1 bis n: Lösungen
        for i in range(num_solutions):
            with tabs[i + 1]:
                uploaded = self.upload_solution(i)
                if uploaded:
                    self.streamlit(i)


        # Letzter Tab: Vergleich
        with tabs[-1]:
            self.compare_results()