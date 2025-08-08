import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import random
import datetime as dt

include_attachments = False
include_blocking_in_gantt = True

class SolutionApp:
    def __init__(self):
        self.solution_data = dict()
        self.instance_data = None
        #self.instance_folder = os.path.join(os.path.dirname(__file__), "Instanzen")
        
        self.number_sites = 0
        self.number_shifts = 0

    def upload_instance(self):
        uploaded_instance = st.file_uploader("Instanz-Datei hochladen", type=["json"], key="instance_uploader")
        if uploaded_instance:
            self.instance_data = json.load(uploaded_instance)
            st.success("Instanzdatei erfolgreich hochgeladen!")

            self.number_sites = len(self.instance_data["Auftraege"])
            self.number_shifts = len(self.instance_data["Bestellpositionen"])
            self.number_machines = len(self.instance_data["Maschinen"])
            self.number_worker = len(self.instance_data["Arbeiter"])
            if include_attachments:
                self.number_attachments = len(self.instance_data["Anbaugeraete"])

            # Instanzdaten als Info ausgeben
            if include_attachments:
                st.info(
                    f"**Instanzdaten:**\n"
                    f"- Anzahl Baustellen: {self.number_sites}\n"
                    f"- Anzahl Bestellpositionen: {self.number_shifts}\n"
                    f"- Anzahl Arbeiter: {self.number_worker}\n"
                    f"- Anzahl Maschinen: {self.number_machines}\n"
                    f"- Anzahl Anbaugeräte: {self.number_attachments}"
                )
            else:
                st.info(
                    f"**Instanzdaten:**\n"
                    f"- Anzahl Baustellen: {self.number_sites}\n"
                    f"- Anzahl Bestellpositionen: {self.number_shifts}\n"
                    f"- Anzahl Arbeiter: {self.number_worker}\n"
                    f"- Anzahl Maschinen: {self.number_machines}"
                )


            self.worker_location = [
                [worker["Wohnort"]["Item1"], worker["Wohnort"]["Item2"]]
                for worker in self.instance_data["Arbeiter"]
            ]

            self.site_location = [
                [site["Standort"]["Item1"], site["Standort"]["Item2"]]
                for site in self.instance_data["Auftraege"]
            ]

            # Karte mit Standorten der Arbeiter und Baustellen anzeigen
            st.write("### Standorte der Arbeiter und Baustellen")

            # DataFrame für die Standorte erstellen
            df_workers = pd.DataFrame(self.worker_location, columns=["lat", "lon"])
            df_workers["Typ"] = "Arbeiter"
            df_sites = pd.DataFrame(self.site_location, columns=["lat", "lon"])
            df_sites["Typ"] = "Baustelle"

            df_map = pd.concat([df_workers, df_sites], ignore_index=True)

            # Farben für die Typen
            color_map = {"Arbeiter": "blue", "Baustelle": "red"}
            df_map["Farbe"] = df_map["Typ"].map(color_map)

            # Plotly Scattermapbox verwenden
            fig = px.scatter_mapbox(
                df_map,
                lat="lat",
                lon="lon",
                color="Typ",
                color_discrete_map=color_map,
                hover_name="Typ",
                zoom=6,
                height=500,
            )

            fig.update_layout(mapbox_style="open-street-map")
            fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

            st.plotly_chart(fig, use_container_width=True)

    def upload_solution(self, key):
        uploaded_solution = st.file_uploader("Lösungsdatei hochladen", type=["json"], key=f"solution_uploader_{key}")
        if uploaded_solution:
            single_solution = SolutionData(json.load(uploaded_solution), key)
            self.solution_data[key] = single_solution
            st.success("Lösungsdatei erfolgreich hochgeladen!")
            return True

    def show_worker_gantt(self, solution_data, key):
        worker_assignments = solution_data.worker_assignments

        # --- reguläre Schichten
        solution_data.worker_rows = [
            {
                'Arbeiter': worker,
                'Start': shift['Start'],
                'Ende': shift['Ende'],
                'Schichttyp': 'Frühschicht' if pd.to_datetime(shift['Start']).hour < 14 else 'Spätschicht',
                'Baustelle': shift['Auftragsnummer']
            }
            for worker, shifts in worker_assignments.items() for shift in shifts
        ]
        df_regular = pd.DataFrame(solution_data.worker_rows)

        # --- optional: blocking Schichten
        if include_blocking_in_gantt:
            worker_blocking = getattr(solution_data, "worker_blocking", {})
            blocking_rows = [
                {
                    'Arbeiter': worker,
                    'Start': shift['Start'],
                    'Ende': shift['Ende'],
                    'Schichttyp': 'Blockiert',
                    'Baustelle': None
                }
                for worker, shifts in worker_blocking.items() for shift in shifts
            ]
            df_blocking = pd.DataFrame(blocking_rows) if blocking_rows else pd.DataFrame(columns=df_regular.columns)
            solution_data.df_worker = pd.concat([df_regular, df_blocking], ignore_index=True)
        else:
            solution_data.df_worker = df_regular.copy()

        if solution_data.df_worker.empty:
            st.info("Keine Arbeiterzuweisungen vorhanden.")
            return

        # Sortierung wie gehabt
        solution_data.df_worker['Arbeiter'] = pd.Categorical(
            solution_data.df_worker['Arbeiter'],
            categories=sorted(solution_data.df_worker['Arbeiter'].dropna().unique(), key=lambda x: int(x.split('_')[1]), reverse=True)
        )
        sorted_workers = sorted(solution_data.df_worker['Arbeiter'].dropna().unique(), key=lambda x: int(x.split('_')[1]), reverse=True)

        # Kennzahlen nur aus regulären Schichten
        if not df_regular.empty:
            solution_data.worker_site_count = (
                df_regular.groupby('Arbeiter', observed=False)['Baustelle'].nunique().to_dict()
            )
            solution_data.worker_site_count = {str(w.split('_')[1]): s for w, s in solution_data.worker_site_count.items()}

            solution_data.worker_shift_type_count = (
                df_regular.assign(
                    Schichttyp=df_regular['Start'].apply(lambda x: 'Frühschicht' if pd.to_datetime(x).hour < 14 else 'Spätschicht')
                )
                .groupby(['Arbeiter', 'Schichttyp'], observed=False)
                .size().unstack(fill_value=0).rename_axis(None, axis=1).to_dict(orient='index')
            )
            solution_data.worker_shift_type_count = {str(w.split('_')[1]): d for w, d in solution_data.worker_shift_type_count.items()}
        else:
            solution_data.worker_site_count = {}
            solution_data.worker_shift_type_count = {}

        # Farben
        color_map = {"Frühschicht": "red", "Spätschicht": "blue"}
        if include_blocking_in_gantt:
            color_map["Blockiert"] = "black"

        # Gantt
        fig_worker = px.timeline(
            solution_data.df_worker,
            x_start="Start",
            x_end="Ende",
            y="Arbeiter",
            color="Schichttyp",
            title="Arbeiterzuweisungen nach Schichttyp" + (" (inkl. Blockierungen)" if include_blocking_in_gantt else ""),
            color_discrete_map=color_map,
            category_orders={"Arbeiter": sorted_workers}
        )

        # “Blockiert”-Balken schraffieren
        if include_blocking_in_gantt:
            fig_worker.for_each_trace(
                lambda tr: tr.update(
                    marker=dict(
                        color="black",
                        pattern=dict(
                            shape="/",       # Muster: Schräg rechts
                            size=8,          # Mustergröße
                            solidity=0.5     # Muster-Deckung (0=transparent, 1=voll)
                        ),
                        line=dict(color="black", width=0.001)  # optional: Umrandung
                    ),
                    opacity=0.9
                ) if tr.name == "Blockiert" else ()
            )

        # Wochenenden hervorheben
        start_date = pd.to_datetime(solution_data.df_worker['Start']).min().date()
        end_date = pd.to_datetime(solution_data.df_worker['Ende']).max().date()
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

        st.plotly_chart(fig_worker, key=f"worker_gantt_{key}")

    def show_machine_gantt(self, solution_data, key):
        # --- Gantt-Diagramm: Maschinen + (optional) Anbaugeräte ---
        machine_assignments = solution_data.machine_assignments
        machine_blocking = getattr(solution_data, "machine_blocking", {})

        if include_attachments:
            attachment_assignments = solution_data.attachment_assignments
            attachment_blocking = getattr(solution_data, "attachment_blocking", {})

        # --- Nutzungszeilen (produktive Einsätze) ---
        solution_data.machine_rows = [
            {
                'Maschine': machine,
                'Start': usage['Start'],
                'Ende': usage['Ende'],
                'Baustelle': usage['Auftragsnummer'],  # .split("-")[0] falls nötig
                'Dauer': usage['Dauer'],
                'Typ': 'Einsatz'
            }
            for machine, usages in machine_assignments.items() for usage in usages
        ]

        if include_attachments:
            solution_data.attachment_rows = [
                {
                    'Maschine': attachment,
                    'Start': usage['Start'],
                    'Ende': usage['Ende'],
                    'Baustelle': usage['Auftragsnummer'],
                    'Dauer': usage['Dauer'],
                    'Typ': 'Einsatz'
                }
                for attachment, usages in attachment_assignments.items() for usage in usages
            ]
        else:
            solution_data.attachment_rows = []

        # --- Blocking-Zeilen (Urlaub/Wartung/Sperre etc.) ---
        if include_blocking_in_gantt:
            machine_block_rows = [
                {
                    'Maschine': machine,
                    'Start': blk['Start'],
                    'Ende': blk['Ende'],
                    'Baustelle': "Blockiert",
                    'Dauer': blk.get('Dauer', (pd.to_datetime(blk['Ende']) - pd.to_datetime(blk['Start'])).total_seconds() / 3600.0),
                    'Typ': 'Blockiert'
                }
                for machine, blks in machine_blocking.items() for blk in blks
            ]
            if include_attachments:
                attachment_block_rows = [
                    {
                        'Maschine': attachment,
                        'Start': blk['Start'],
                        'Ende': blk['Ende'],
                        'Baustelle': "Blockiert",
                        'Dauer': blk.get('Dauer', (pd.to_datetime(blk['Ende']) - pd.to_datetime(blk['Start'])).total_seconds() / 3600.0),
                        'Typ': 'Blockiert'
                    }
                    for attachment, blks in attachment_blocking.items() for blk in blks
                ]
            else:
                attachment_block_rows = []
        else:
            machine_block_rows = []
            attachment_block_rows = []

        # --- DataFrame bauen ---
        df_machine = pd.DataFrame(
            solution_data.machine_rows + solution_data.attachment_rows + machine_block_rows + attachment_block_rows
        )

        if df_machine.empty:
            st.info("Keine Maschinenzuweisungen vorhanden.")
            return

        # Statistikdaten (nur auf echter Nutzung basieren, nicht auf Blockings)
        df_usage_only = df_machine[df_machine['Typ'] == 'Einsatz'].copy()
        solution_data.stunden_in_nutzung_dict = df_usage_only.groupby('Maschine')['Dauer'].sum().to_dict()
        solution_data.tage_in_nutzung_dict = {k: v / 24 for k, v in solution_data.stunden_in_nutzung_dict.items()}
        solution_data.maschinen_anzahl_baustellen_dict = df_usage_only.groupby('Maschine')['Baustelle'].nunique().to_dict()

        # Farben für Baustellen
        unique_sites = sorted(df_usage_only['Baustelle'].unique())  # Farben nur für echte Baustellen
        color_map = {
            site: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
            for i, site in enumerate(unique_sites)
        }
        # Farbe/Muster für Blockings ergänzen, falls sichtbar
        if include_blocking_in_gantt:
            color_map["Blockiert"] = "black"

        # Maschinenreihenfolge (erst Maschinen, dann Anbaugeräte — in Eingabereihenfolge)
        ordered_names = list(dict.fromkeys(df_machine['Maschine'].tolist()))

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
                "Baustelle": (unique_sites + (["Blockiert"] if include_blocking_in_gantt else [])),
                "Maschine": ordered_names
            }
        )
        fig_machine.update_yaxes(autorange="reversed")

        # “Blockiert” schraffieren & dunkler zeichnen (nur wenn aktiv)
        if include_blocking_in_gantt:
            fig_machine.for_each_trace(
                lambda tr: tr.update(
                    marker=dict(
                        color="black",
                        pattern=dict(
                            shape="/",   # Schräg rechts
                            size=8,
                            solidity=0.5
                        ),
                        line=dict(color="black", width=1)  # schwarze Kontur
                    ),
                    opacity=0.9
                ) if tr.name == "Blockiert" else ()
            )

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

        st.plotly_chart(fig_machine, key=f"machine_gantt_{key}")


    def general_statistics(self, solution_data):
        # --- Statistische Kennzahlen ---

        # Rechenzeit in Minuten
        solution_data.run_time_minutes = solution_data.raw["RechenzeitInSekunden"] / 60

        # Erreichte Baustellen (%)
        solution_data.finished_sites = len({key.split("-")[0] for key, val in solution_data.raw["BerechnetAuftragBearbeitet"].items() if val})
        solution_data.finished_sites_percentage = (solution_data.finished_sites / self.number_sites) * 100

        # Erreichte Bestellpositionen (%)
        if len(solution_data.machine_rows) != len(solution_data.worker_rows):
            st.warning("Die Anzahl der Maschinen und Arbeiter stimmt nicht überein. Bitte überprüfen Sie die Daten.")
            return
        solution_data.finished_shifts = len(solution_data.machine_rows)
        solution_data.finished_shifts_percentage = (solution_data.finished_shifts / self.number_shifts) * 100

        # Bestellpositionen welche von nicht regulären Arbeitern bearbeitet wurden
        solution_data.non_regular_driver = sum(solution_data.raw["MaschinenLoesung"]["BerechneteStammfahrerVerletzungenProMaschine"].values())
        solution_data.non_regular_driver_percentage = (solution_data.non_regular_driver / solution_data.finished_shifts) * 100

        # Anzahl BaustellKenntnis Verletzungen
        solution_data.total_site_knowledge_violation = sum(solution_data.raw["Arbeiterloesung"]["AnzahlBaustellKenntnisVerletzungen"].values())
        solution_data.site_knowledge_violation = {}
        for worker, violations in solution_data.raw["Arbeiterloesung"]["AnzahlBaustellKenntnisVerletzungen"].items():
            worker = str(worker.split("_")[1])
            solution_data.site_knowledge_violation[worker] = violations

        # Anteil genutzter Maschinen
        solution_data.machine_count = sum(solution_data.raw["MaschinenLoesung"]["BerechnetMaschineGenutzt"].values())
        solution_data.machine_count_percentage = (solution_data.machine_count / self.number_machines) * 100
        solution_data.unued_machine_count = self.number_machines - solution_data.machine_count

        # Anteil genutzter Arbeiter
        solution_data.worker_count = sum(solution_data.raw["Arbeiterloesung"]["BerechnetArbeiterGenutzt"].values())
        solution_data.worker_count_percentage = (solution_data.worker_count / self.number_worker) * 100
        solution_data.unued_worker_count = self.number_worker - solution_data.worker_count

        if include_attachments:
            # Anteil genutzter Anbaugeräte
            solution_data.attachment_count = sum(solution_data.raw["AnbaugeraeteLoesung"]["BerechnetAnbaugeraetGenutzt"].values())
            solution_data.attachment_count_percentage = (solution_data.attachment_count / self.number_attachments) * 100
            solution_data.unued_attachment_count = self.number_attachments - solution_data.attachment_count

        # Gesamttransportdistanz der Maschinen
        solution_data.transport_distance_machine = sum(solution_data.raw["MaschinenLoesung"]["BerechneteKilometer"].values())

        # Gesamtarbeitswege der Arbeiter
        solution_data.comute_distance_worker = sum(solution_data.raw["Arbeiterloesung"]["BerechneteKilometer"].values())

        if include_attachments:
            # Gesamttransportdistanz der Anbaugeräte
            solution_data.transport_distance_attachment = sum(solution_data.raw["AnbaugeraeteLoesung"]["BerechneteKilometer"].values())

        # Arbeitszeiten der Arbeiter
        for worker, shifts in solution_data.worker_assignments.items():
            worker = str(worker.split("_")[1])
            solution_data.worker_hours[worker] = sum(shift['Dauer'] for shift in shifts)

        solution_data.target_average_work_hours = sum(dauer for dauer in solution_data.worker_hours.values()) / solution_data.worker_count
        solution_data.total_deviation_from_target = sum(abs(dauer - solution_data.target_average_work_hours) for dauer in solution_data.worker_hours.values())

        # Nutzungsstunden der Maschinen
        for machine, shifts in solution_data.machine_assignments.items():
            solution_data.machine_hours[machine] = sum(shift['Dauer'] for shift in shifts)

        if include_attachments:
            # Nutzungsstunden der Anbaugeräte
            for attachment, shifts in solution_data.attachment_assignments.items():
                solution_data.attachment_hours[attachment] = sum(shift['Dauer'] for shift in shifts)


    def construction_statistics(self, solution_data):
        
        # --- Statistische Kennzahlen ausgeben ---
        st.write("")
        st.write("#### Baustellen und Bestellpositionen")
        st.write(f"**Erreichte Baustellen:** {solution_data.finished_sites} von {self.number_sites} ➡️ {solution_data.finished_sites_percentage:.1f}%")
        st.write(f"**Erreichte Bestellpositionen:** {solution_data.finished_shifts} von {self.number_shifts} ➡️ {solution_data.finished_shifts_percentage:.1f}%")
        st.write(f"**Anzahl Stammfahrerverletzungen:** {solution_data.non_regular_driver} von {solution_data.finished_shifts} ➡️ {solution_data.non_regular_driver_percentage:.1f}%")
        
        # --- Tabelle: Anzahl der Bestellpositionen pro Baustelle mit dezenter farblicher Markierung ---
        
        # Tabelle erstellen
        baustellen_rows = []
        for order in self.instance_data["Auftraege"]:
            order_number = int(order["Auftragsnummer"])
            order_item_count = len(order["BestellpositionenStrings"])
            # Status anhand von "BerechnetAuftragBearbeitet" bestimmen, wobei der Key mit "Auftrag <order_number>" beginnt
            status = False
            for k, v in solution_data.raw["BerechnetAuftragBearbeitet"].items():
                if k.startswith(f"Auftrag {order_number}"):
                    status = v
                    break

            baustellen_rows.append({
                "Baustelle": order_number,
                "Bestellpositionen": order_item_count,
                "Status": "✅" if status else "❌"
            })
            
        # DataFrame erstellen
        df_sites = pd.DataFrame(baustellen_rows)
        # Index entfernen
        df_sites = df_sites.set_index("Baustelle")

        st.dataframe(df_sites)

        #  --- Diagramm: Anzahl der Bestellpositionen pro Baustelle ---
        df_sites_sorted = df_sites.reset_index().sort_values(by="Bestellpositionen", ascending=True)

        # Add a new column for a generic X-axis label (e.g., "Site 1", "Site 2")
        df_sites_sorted['Baustelle_Index'] = range(1, len(df_sites_sorted) + 1)

        # Define colors for the status
        colors = {
            "✅": "green",
            "❌": "red"
        }

        # Create the bar chart
        fig = px.bar(
            df_sites_sorted,
            x="Baustelle_Index",
            y="Bestellpositionen",
            color="Status",
            title="Baustellen-Bestellpositionen",
            color_discrete_map=colors,
            hover_data={"Baustelle": True, "Baustelle_Index": False}
        )

        # Update X-axis to hide labels
        fig.update_layout(
            xaxis_title="",
            xaxis_showticklabels=False
        )

        # Display the chart in Streamlit
        st.plotly_chart(fig, key=f"baustellen_chart_{solution_data.key}")

    def worker_statistics(self, solution_data):

        # --- Statistische Kennzahlen ausgeben ---
        st.write("")
        st.write("#### Arbeiter")
        st.write(f"**Anteil genutzte Arbeiter:** {solution_data.worker_count} von {self.number_worker} ➡️ {solution_data.worker_count_percentage:.1f}%")
        st.write(f"**Gesamtarbeitswegedistanz:** {solution_data.comute_distance_worker:.1f} km")
        st.write(f"**Ziel Durchschnittsstunden:** {solution_data.target_average_work_hours:.1f} Stunden")
        st.write(f"**Gesamtabweichung vom Ziel:** {solution_data.total_deviation_from_target:.1f} Stunden")
        st.write(f"**Anzahl Baustellkenntnis Verletzungen:** {solution_data.total_site_knowledge_violation}")
        st.write("")


        # --- Tabelle: Arbeitszeiten der Arbeiter ---
        df_arbeitszeiten = pd.DataFrame.from_dict(solution_data.worker_hours, orient='index', columns=['Gesamtstunden'])
        df_arbeitszeiten.index.name = 'Arbeiter_ID'
        df_arbeitszeiten['Abweichung Ziel'] = round(df_arbeitszeiten['Gesamtstunden'] - (sum(dauer for dauer in solution_data.worker_hours.values()) / solution_data.worker_count), 1)
        df_arbeitszeiten['Monatsauslastung'] = ((df_arbeitszeiten['Gesamtstunden'] / 160) * 100).round(1).astype(str) + '%'
        df_arbeitszeiten['Frühschichten'] = [solution_data.worker_shift_type_count.get(k, {}).get('Frühschicht', 0) for k in df_arbeitszeiten.index]
        df_arbeitszeiten['Spätschichten'] = [solution_data.worker_shift_type_count.get(k, {}).get('Spätschicht', 0) for k in df_arbeitszeiten.index]
        df_arbeitszeiten['Baustellen'] = [solution_data.worker_site_count.get(k, 0) for k in df_arbeitszeiten.index]
        df_arbeitszeiten['Baustellenverletzung'] = [solution_data.site_knowledge_violation.get(k, 0) for k in df_arbeitszeiten.index]
        df_arbeitszeiten['Arbeitsweg'] = [round(solution_data.raw["Arbeiterloesung"]["BerechneteKilometer"].get(f"Arbeiter_{k}", 0), 2)for k in df_arbeitszeiten.index]
        st.dataframe(df_arbeitszeiten)
        st.write(f"➡️ **Anzahl nicht eingesetzter Arbeiter:** {solution_data.unued_worker_count}")

        # Durchschnitts-, Minimal- und Maximalwerte unter der Tabelle anzeigen
        # Nur Zeilen mit Gesamtstunden > 0 berücksichtigen
        df_arbeitszeiten_nonzero = df_arbeitszeiten[df_arbeitszeiten['Gesamtstunden'] > 0]
        if not df_arbeitszeiten_nonzero.empty:
            avg_gesamtstunden = df_arbeitszeiten_nonzero['Gesamtstunden'].mean()
            min_gesamtstunden = df_arbeitszeiten_nonzero['Gesamtstunden'].min()
            max_gesamtstunden = df_arbeitszeiten_nonzero['Gesamtstunden'].max()

            avg_frueh = df_arbeitszeiten_nonzero['Frühschichten'].mean()
            min_frueh = df_arbeitszeiten_nonzero['Frühschichten'].min()
            max_frueh = df_arbeitszeiten_nonzero['Frühschichten'].max()

            avg_spaet = df_arbeitszeiten_nonzero['Spätschichten'].mean()
            min_spaet = df_arbeitszeiten_nonzero['Spätschichten'].min()
            max_spaet = df_arbeitszeiten_nonzero['Spätschichten'].max()

            avg_baustellen = df_arbeitszeiten_nonzero['Baustellen'].mean()
            min_baustellen = df_arbeitszeiten_nonzero['Baustellen'].min()
            max_baustellen = df_arbeitszeiten_nonzero['Baustellen'].max()

            avg_arbeitsweg = df_arbeitszeiten_nonzero['Arbeitsweg'].mean()
            min_arbeitsweg = df_arbeitszeiten_nonzero['Arbeitsweg'].min()
            max_arbeitsweg = df_arbeitszeiten_nonzero['Arbeitsweg'].max()

    
            st.markdown(
            f"**Durchschnitt:** "
            f"Gesamtstunden: {avg_gesamtstunden:.1f} | "
            f"Frühschichten: {avg_frueh:.1f} | "
            f"Spätschichten: {avg_spaet:.1f} | "
            f"Baustellen: {avg_baustellen:.1f} | "
            f"Arbeitsweg: {avg_arbeitsweg:.1f} km"
            )
            st.markdown(
            f"**Minimum:** "
            f"Gesamtstunden: {min_gesamtstunden:.1f} | "
            f"Frühschichten: {min_frueh:.1f} | "
            f"Spätschichten: {min_spaet:.1f} | "
            f"Baustellen: {min_baustellen:.1f} | "
            f"Arbeitsweg: {min_arbeitsweg:.1f} km"
            )
            st.markdown(
            f"**Maximum:** "
            f"Gesamtstunden: {max_gesamtstunden:.1f} | "
            f"Frühschichten: {max_frueh:.1f} | "
            f"Spätschichten: {max_spaet:.1f} | "
            f"Baustellen: {max_baustellen:.1f} | "
            f"Arbeitsweg: {max_arbeitsweg:.1f} km"
            )

            solution_data.averages["Arbeiter"] = {
                # Arbeitsstunden
                "Gesamtstunden Durchschnitt": avg_gesamtstunden,
                "Gesamtstunden Minimum": min_gesamtstunden,
                "Gesamtstunden Maximum": max_gesamtstunden,
                # Frühschichten
                "Frühschichten Durchschnitt": avg_frueh,
                "Frühschichten Minimum": min_frueh,
                "Frühschichten Maximum": max_frueh,
                # Spätschichten
                "Spätschichten Durchschnitt": avg_spaet,
                "Spätschichten Minimum": min_spaet,
                "Spätschichten Maximum": max_spaet,
                # Baustellen
                "Baustellen Durchschnitt": avg_baustellen,
                "Baustellen Minimum": min_baustellen,
                "Baustellen Maximum": max_baustellen,
                # Arbeitsweg
                "Arbeitsweg Durchschnitt": avg_arbeitsweg,
                "Arbeitsweg Minimum": min_arbeitsweg,
                "Arbeitsweg Maximum": max_arbeitsweg,
            }

        # --- Histogramm: Arbeitsstundenverteilung der Arbeiter ---
        # Nur Arbeiter mit mehr als 0 Stunden berücksichtigen
        worker_hours_values = [v for v in solution_data.worker_hours.values() if v > 0]
        # Definiere die Bins explizit, damit 140-160 ein 20er Bin ist
        bins = [0, 20, 40, 60, 80, 100, 120, 140, 160]
        fig = px.histogram(
            x=worker_hours_values,
            category_orders={"x": bins},
            title="Auslastungsverteilung der Arbeitszeiten",
            labels={'x': 'Arbeitsstunden'},
            histnorm='percent',  # Prozentuale Darstellung auf der Y-Achse
            color_discrete_sequence=['#636EFA'],
            nbins=len(bins)-1
        )
        fig.update_traces(
            xbins=dict(
            start=bins[0],
            end=bins[-1],
            size=20  # 20er Bins
            ),
            hovertemplate="<b>Arbeitsstunden:</b> %{x}<br><b>Anteil Arbeiter:</b> %{y:.1f}%<extra></extra>"
        )
        # vertikale rote dashen Linie hinzufügen bis zu maximalen y-Wert
        fig.add_vline(x=solution_data.target_average_work_hours, line_dash="dash", line_color="red")

        # Y-Achsen-Label und X-Achsen-Bereich festlegen
        fig.update_layout(
            yaxis_title='Anteil der eingesetzten Arbeiter (%)',
            bargap=0.1,
            xaxis_title='Arbeitsstunden',
            xaxis=dict(range=[0, 160])  # X-Achse immer von 0 bis 160 anzeigen
        )

        # Diagramm in Streamlit anzeigen
        st.plotly_chart(fig, key=f"arbeitszeiten_histogram_{solution_data.key}")

    
    def machine_statistics(self, solution_data):

        # --- Statistische Kennzahlen ausgeben ---
        st.write("")
        st.write("#### Maschinen")
        st.write(f"**Anteil genutzte Maschinen:** {solution_data.machine_count} von {self.number_machines} ➡️ {solution_data.machine_count_percentage:.1f}%")
        st.write(f"**Gesamttransportdistanz der Maschinen:** {solution_data.transport_distance_machine:.1f} km")
        st.write("")

        # --- Tabelle: Maschinennutzung ---
        df_maschinennutzung = pd.DataFrame.from_dict(solution_data.machine_hours, orient='index', columns=['Gesamtstunden'])
        df_maschinennutzung.index.name = 'Maschine'
        df_maschinennutzung['Baustellen'] = [solution_data.maschinen_anzahl_baustellen_dict.get(k, 0) for k in df_maschinennutzung.index]
        df_maschinennutzung['Tage in Nutzung'] = [round(solution_data.tage_in_nutzung_dict.get(k, 0), 2) for k in df_maschinennutzung.index]
        df_maschinennutzung['Transportdistanz'] = [round(solution_data.raw["MaschinenLoesung"]["BerechneteKilometer"].get(k, 0), 2) for k in df_maschinennutzung.index]
        df_maschinennutzung['Stammfahrerverletzungen'] = [solution_data.raw["MaschinenLoesung"]["BerechneteStammfahrerVerletzungenProMaschine"].get(k, 0) for k in df_maschinennutzung.index]
        st.dataframe(df_maschinennutzung)
        st.write(f"➡️ **Anzahl nicht eingesetzter Maschinen:** {solution_data.unued_machine_count}")
        # Durchschnitts-, Minimal- und Maximalwerte unter der Tabelle anzeigen
        # Nur Zeilen mit Gesamtstunden > 0 berücksichtigen
        df_maschinennutzung_nonzero = df_maschinennutzung[df_maschinennutzung['Gesamtstunden'] > 0]
        if not df_maschinennutzung_nonzero.empty:
            avg_gesamtstunden = df_maschinennutzung_nonzero['Gesamtstunden'].mean()
            min_gesamtstunden = df_maschinennutzung_nonzero['Gesamtstunden'].min()
            max_gesamtstunden = df_maschinennutzung_nonzero['Gesamtstunden'].max()

            avg_baustellen = df_maschinennutzung_nonzero['Baustellen'].mean()
            min_baustellen = df_maschinennutzung_nonzero['Baustellen'].min()
            max_baustellen = df_maschinennutzung_nonzero['Baustellen'].max()

            avg_tage_nutzung = df_maschinennutzung_nonzero['Tage in Nutzung'].mean()
            min_tage_nutzung = df_maschinennutzung_nonzero['Tage in Nutzung'].min()
            max_tage_nutzung = df_maschinennutzung_nonzero['Tage in Nutzung'].max()

            avg_transportdistanz = df_maschinennutzung_nonzero['Transportdistanz'].mean()
            min_transportdistanz = df_maschinennutzung_nonzero['Transportdistanz'].min()
            max_transportdistanz = df_maschinennutzung_nonzero['Transportdistanz'].max()

            avg_stammfahrer = df_maschinennutzung_nonzero['Stammfahrerverletzungen'].mean()
            min_stammfahrer = df_maschinennutzung_nonzero['Stammfahrerverletzungen'].min()
            max_stammfahrer = df_maschinennutzung_nonzero['Stammfahrerverletzungen'].max()

            st.markdown(
            f"**Durchschnitt:** "
            f"Gesamtstunden: {avg_gesamtstunden:.1f} | "
            f"Baustellen: {avg_baustellen:.1f} | "
            f"Tage in Nutzung: {avg_tage_nutzung:.2f} | "
            f"Transportdistanz: {avg_transportdistanz:.2f} km | "
            f"Stammfahrerverletzungen: {avg_stammfahrer:.1f}"
            )
            st.markdown(
            f"**Minimum:** "
            f"Gesamtstunden: {min_gesamtstunden:.1f} | "
            f"Baustellen: {min_baustellen:.1f} | "
            f"Tage in Nutzung: {min_tage_nutzung:.2f} | "
            f"Transportdistanz: {min_transportdistanz:.2f} km | "
            f"Stammfahrerverletzungen: {min_stammfahrer:.1f}"
            )
            st.markdown(
            f"**Maximum:** "
            f"Gesamtstunden: {max_gesamtstunden:.1f} | "
            f"Baustellen: {max_baustellen:.1f} | "
            f"Tage in Nutzung: {max_tage_nutzung:.2f} | "
            f"Transportdistanz: {max_transportdistanz:.2f} km | "
            f"Stammfahrerverletzungen: {max_stammfahrer:.1f}"
            )
            solution_data.averages["Maschine"] = {
                # Nutzungsdauer
                "Gesamtstunden Durchschnitt": avg_gesamtstunden,
                "Gesamtstunden Minimum": min_gesamtstunden,
                "Gesamtstunden Maximum": max_gesamtstunden,
                # Anzahl Baustellen
                "Baustellen Durchschnitt": avg_baustellen,
                "Baustellen Minimum": min_baustellen,
                "Baustellen Maximum": max_baustellen,
                # Nutzungstage
                "Tage in Nutzung Durchschnitt": avg_tage_nutzung,
                "Tage in Nutzung Minimum": min_tage_nutzung,
                "Tage in Nutzung Maximum": max_tage_nutzung,
                # Transportdistanz
                "Transportdistanz Durchschnitt": avg_transportdistanz,
                "Transportdistanz Minimum": min_transportdistanz,
                "Transportdistanz Maximum": max_transportdistanz,
                # Stammfahrerverletzungen
                "Stammfahrerverletzungen Durchschnitt": avg_stammfahrer,
                "Stammfahrerverletzungen Minimum": min_stammfahrer,
                "Stammfahrerverletzungen Maximum": max_stammfahrer,
            }

    def attachment_statistics(self, solution_data):
        
        # --- Statistische Kennzahlen ausgeben ---
        st.write("")
        st.write("#### Anbaugeräte")
        st.write(f"**Anteil genutzte Anbaugeräte:** {solution_data.attachment_count} von {self.number_attachments} ➡️ {solution_data.attachment_count_percentage:.1f}%")
        st.write(f"**Gesamttransportdistanz der Anbaugeräte:** {solution_data.transport_distance_attachment:.1f} km")
        st.write("")

        # --- Tabelle: Anbaugerätenutzung ---
        df_anbaugerätenutzung = pd.DataFrame.from_dict(solution_data.attachment_hours, orient='index', columns=['Gesamtstunden'])
        df_anbaugerätenutzung.index.name = 'Anbaugerät'
        df_anbaugerätenutzung['Baustellen'] = [solution_data.maschinen_anzahl_baustellen_dict.get(k, 0) for k in df_anbaugerätenutzung.index]
        df_anbaugerätenutzung['Tage in Nutzung'] = [round(solution_data.tage_in_nutzung_dict.get(k, 0), 2) for k in df_anbaugerätenutzung.index]
        df_anbaugerätenutzung['Transportdistanz'] = [round(solution_data.raw["AnbaugeraeteLoesung"]["BerechneteKilometer"].get(k, 0), 2) for k in df_anbaugerätenutzung.index]
        st.dataframe(df_anbaugerätenutzung)
        st.write(f"➡️ **Anzahl nicht eingesetzter Anbaugeräte:** {solution_data.unued_attachment_count}")
        # Durchschnitts-, Minimal- und Maximalwerte unter der Tabelle anzeigen
        # Nur Zeilen mit Gesamtstunden > 0 berücksichtigen
        df_anbaugerätenutzung_nonzero = df_anbaugerätenutzung[df_anbaugerätenutzung['Gesamtstunden'] > 0]
        if not df_anbaugerätenutzung_nonzero.empty:
            avg_gesamtstunden = df_anbaugerätenutzung_nonzero['Gesamtstunden'].mean()
            min_gesamtstunden = df_anbaugerätenutzung_nonzero['Gesamtstunden'].min()
            max_gesamtstunden = df_anbaugerätenutzung_nonzero['Gesamtstunden'].max()

            avg_baustellen = df_anbaugerätenutzung_nonzero['Baustellen'].mean()
            min_baustellen = df_anbaugerätenutzung_nonzero['Baustellen'].min()
            max_baustellen = df_anbaugerätenutzung_nonzero['Baustellen'].max()

            avg_tage_nutzung = df_anbaugerätenutzung_nonzero['Tage in Nutzung'].mean()
            min_tage_nutzung = df_anbaugerätenutzung_nonzero['Tage in Nutzung'].min()
            max_tage_nutzung = df_anbaugerätenutzung_nonzero['Tage in Nutzung'].max()

            avg_transportdistanz = df_anbaugerätenutzung_nonzero['Transportdistanz'].mean()
            min_transportdistanz = df_anbaugerätenutzung_nonzero['Transportdistanz'].min()
            max_transportdistanz = df_anbaugerätenutzung_nonzero['Transportdistanz'].max()

            st.markdown(
            f"**Durchschnitt:** "
            f"Gesamtstunden: {avg_gesamtstunden:.1f} | "
            f"Baustellen: {avg_baustellen:.1f} | "
            f"Tage in Nutzung: {avg_tage_nutzung:.2f} | "
            f"Transportdistanz: {avg_transportdistanz:.2f} km"
            )
            st.markdown(
            f"**Minimum:** "
            f"Gesamtstunden: {min_gesamtstunden:.1f} | "
            f"Baustellen: {min_baustellen:.1f} | "
            f"Tage in Nutzung: {min_tage_nutzung:.2f} | "
            f"Transportdistanz: {min_transportdistanz:.2f} km"
            )
            st.markdown(
            f"**Maximum:** "
            f"Gesamtstunden: {max_gesamtstunden:.1f} | "
            f"Baustellen: {max_baustellen:.1f} | "
            f"Tage in Nutzung: {max_tage_nutzung:.2f} | "
            f"Transportdistanz: {max_transportdistanz:.2f} km"
            )
            solution_data.averages["Anbaugerät"] = {
                "Gesamtstunden Durchschnitt": avg_gesamtstunden,
                "Gesamtstunden Minimum": min_gesamtstunden,
                "Gesamtstunden Maximum": max_gesamtstunden,
                "Baustellen Durchschnitt": avg_baustellen,
                "Baustellen Minimum": min_baustellen,
                "Baustellen Maximum": max_baustellen,
                "Tage in Nutzung Durchschnitt": avg_tage_nutzung,
                "Tage in Nutzung Minimum": min_tage_nutzung,
                "Tage in Nutzung Maximum": max_tage_nutzung,
                "Transportdistanz Durchschnitt": avg_transportdistanz,
                "Transportdistanz Minimum": min_transportdistanz,
                "Transportdistanz Maximum": max_transportdistanz,
            }



    def streamlit(self, key):
        current_solution_data = self.solution_data[key]
        current_solution_data.averages = {}

        # --- Gantt-Diagramm ---
        st.subheader("Gantt-Diagrammme")
        self.show_worker_gantt(current_solution_data, key)
        self.show_machine_gantt(current_solution_data, key)

        # --- Statistiken ---
        self.general_statistics(current_solution_data)
        st.subheader("Baustellen und Bestellpositionen")
        # Baustellen und Bestellpositionen
        self.construction_statistics(current_solution_data)
        # Arbeiter
        self.worker_statistics(current_solution_data)
        # Maschinen
        self.machine_statistics(current_solution_data)
        if include_attachments:
            # Anbaugeräte
            self.attachment_statistics(current_solution_data)



    def compare_results(self):
        st.write("## Vergleich der Lösungen")

        if len(self.solution_data) < 2:
            st.info("Bitte mindestens zwei Lösungen hochladen, um einen Vergleich anzuzeigen.")
            return

        # Instanzdaten als Info ausgeben
        if include_attachments:
            st.info(
                f"**Instanzdaten:**\n"
                f"- Anzahl Baustellen: {self.number_sites}\n"
                f"- Anzahl Bestellpositionen: {self.number_shifts}\n"
                f"- Anzahl Arbeiter: {self.number_worker}\n"
                f"- Anzahl Maschinen: {self.number_machines}\n"
                f"- Anzahl Anbaugeräte: {self.number_attachments}"
            )
            # Liste der Keys und Emojis für die Lösungen
            solution_keys = list(self.solution_data.keys())
            emojis = st.session_state.get("solution_emojis", [f"Lösung {i+1}" for i in solution_keys])

            # Vergleichstabelle der wichtigsten Kennzahlen (absolute Werte) – nur Lösungen
            rows = []
            for idx, key in enumerate(solution_keys):
                sol = self.solution_data[key]
                row = {
                    "Lösung": emojis[idx] if idx < len(emojis) else f"Lösung {key+1}",
                    "Erreichte Baustellen": sol.finished_sites,
                    "Erreichte Bestellpositionen": sol.finished_shifts,
                    "Stammfahrerverletzungen": sol.non_regular_driver,
                    "Baustellenkenntnisverletzungen": sol.total_site_knowledge_violation,
                    "Abweichung Zielstunden": sol.total_deviation_from_target,
                    "Genutzte Arbeiter": sol.worker_count,
                    "Genutzte Maschinen": sol.machine_count,
                    "Genutzte Anbaugeräte": sol.attachment_count,
                    "Arbeitswegedistanz (km)": f"{sol.comute_distance_worker:.1f}",
                    "Maschinentransport (km)": f"{sol.transport_distance_machine:.1f}",
                    "Anbaugerätetransport (km)": f"{sol.transport_distance_attachment:.1f}",
                    "Rechenzeit (min)": f"{sol.run_time_minutes:.1f}",
                }
                rows.append(row)

            df_compare = pd.DataFrame(rows)
            df_compare = df_compare.set_index("Lösung")
            # Tabelle transponieren: Zeilen werden Spalten, Spalten werden Zeilen
            df_compare_transposed = df_compare.transpose()

            # Die erste Spalte so breit machen wie der längste Text
            # Ermittle die maximale Textlänge in der ersten Spalte
            max_len = df_compare_transposed.index.str.len().max()
            # Setze die Breite (z.B. 8 Pixel pro Zeichen, min 120, max 400)
            col_width = min(max(120, max_len * 8), 400)
            # Zeige die Tabelle mit angepasster erster Spaltenbreite
            st.dataframe(
                df_compare_transposed,
                column_config={df_compare_transposed.columns[0]: st.column_config.Column(width=col_width)}
            )
            

            # Vergleichstabelle der Durchschnittswerte für alle Lösungen
            st.write("### Durchschnittswerte der Lösungen")

            # Sammle alle möglichen Kategorien aus allen Lösungen
            all_categories = set()
            for sol in self.solution_data.values():
                all_categories.update(sol.averages.keys())

            # Für jede Kategorie eine Tabelle anzeigen
            for category in sorted(all_categories):
                rows = []
                columns = set()
                for idx, key in enumerate(solution_keys):
                    sol = self.solution_data[key]
                    avg = sol.averages.get(category, {})
                    row = {"Lösung": emojis[idx] if idx < len(emojis) else f"Lösung {key+1}"}
                    row.update(avg)
                    columns.update(avg.keys())
                    rows.append(row)
                if rows:
                    df_avg = pd.DataFrame(rows)
                    df_avg = df_avg.set_index("Lösung")
                    # Nur die Spalten anzeigen, die auch in dieser Kategorie vorkommen
                    df_avg = df_avg[list(sorted(columns))]
                    st.write(f"**{category.capitalize()}**")
                    st.dataframe(df_avg)

            # Optional: Balkendiagramm für ausgewählte absolute Kennzahlen
            metrics = [
                ("Erreichte Baustellen", "Erreichte Baustellen"),
                ("Erreichte Bestellpositionen", "Erreichte Bestellpositionen"),
                ("Genutzte Arbeiter", "Genutzte Arbeiter"),
                ("Genutzte Maschinen", "Genutzte Maschinen"),
                ("Genutzte Anbaugeräte", "Genutzte Anbaugeräte"),
                ("Arbeitswegedistanz (km)", "Arbeitswegedistanz (km)"),
                ("Maschinentransport (km)", "Maschinentransport (km)"),
                ("Anbaugerätetransport (km)", "Anbaugerätetransport (km)"),
                ("Stammfahrerverletzungen", "Stammfahrerverletzungen"),
                ("Baustellenkenntnisverletzungen", "Baustellenkenntnisverletzungen"),
                ("Abweichung Zielstunden", "Abweichung Zielstunden")
            ]
            instanz_values = {
                "Erreichte Baustellen": self.number_sites,
                "Erreichte Bestellpositionen": self.number_shifts,
                "Genutzte Arbeiter": self.number_worker,
                "Genutzte Maschinen": self.number_machines,
                "Genutzte Anbaugeräte": self.number_attachments,
            }
            for metric, title in metrics:
                df_compare_numeric = df_compare.reset_index().copy()
                df_compare_numeric[metric] = pd.to_numeric(df_compare_numeric[metric], errors="coerce")
                fig = px.bar(
                df_compare_numeric,
                x="Lösung",
                y=metric,
                title=title,
                color="Lösung",
                color_discrete_sequence=px.colors.qualitative.Plotly
                )
                # Instanzwert als horizontale Linie
                instanz_value = instanz_values.get(metric)
                if pd.api.types.is_number(instanz_value):
                    fig.add_hline(y=instanz_value, line_dash="dash", line_color="black", annotation_text="Instanz", annotation_position="top left")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                f"**Instanzdaten:**\n"
                f"- Anzahl Baustellen: {self.number_sites}\n"
                f"- Anzahl Bestellpositionen: {self.number_shifts}\n"
                f"- Anzahl Arbeiter: {self.number_worker}\n"
                f"- Anzahl Maschinen: {self.number_machines}"
            )

            # Liste der Keys und Emojis für die Lösungen
            solution_keys = list(self.solution_data.keys())
            emojis = st.session_state.get("solution_emojis", [f"Lösung {i+1}" for i in solution_keys])

            # Vergleichstabelle der wichtigsten Kennzahlen (absolute Werte) – nur Lösungen
            rows = []
            for idx, key in enumerate(solution_keys):
                sol = self.solution_data[key]
                row = {
                    "Lösung": emojis[idx] if idx < len(emojis) else f"Lösung {key+1}",
                    "Erreichte Baustellen": sol.finished_sites,
                    "Erreichte Bestellpositionen": sol.finished_shifts,
                    "Stammfahrerverletzungen": sol.non_regular_driver,
                    "Baustellenkenntnisverletzungen": sol.total_site_knowledge_violation,
                    "Abweichung Zielstunden": sol.total_deviation_from_target,
                    "Arbeitswegedistanz (km)": round(sol.comute_distance_worker, 1),
                    "Maschinentransport (km)": round(sol.transport_distance_machine, 1),
                    "Rechenzeit (min)": round(sol.run_time_minutes, 1),
                    "Genutzte Arbeiter": sol.worker_count,
                    "Genutzte Maschinen": sol.machine_count,
                }
                rows.append(row)

            df_compare = pd.DataFrame(rows)
            df_compare = df_compare.set_index("Lösung")
            # Tabelle transponieren: Zeilen werden Spalten, Spalten werden Zeilen
            df_compare_transposed = df_compare.transpose()

            # Die erste Spalte so breit machen wie der längste Text
            # Ermittle die maximale Textlänge in der ersten Spalte
            max_len = df_compare_transposed.index.str.len().max()
            # Setze die Breite (z.B. 8 Pixel pro Zeichen, min 120, max 400)
            col_width = min(max(120, max_len * 8), 400)
            # Zeige die Tabelle mit angepasster erster Spaltenbreite
            st.dataframe(
                df_compare_transposed,
                column_config={df_compare_transposed.columns[0]: st.column_config.Column(width=col_width)}
            )
            

            # Vergleichstabelle der Durchschnittswerte für alle Lösungen
            st.write("### Durchschnittswerte der Lösungen")

            # Sammle alle möglichen Kategorien aus allen Lösungen
            all_categories = set()
            for sol in self.solution_data.values():
                all_categories.update(sol.averages.keys())

            # Für jede Kategorie eine Tabelle anzeigen
            for category in sorted(all_categories):
                rows = []
                columns = set()
                for idx, key in enumerate(solution_keys):
                    sol = self.solution_data[key]
                    avg = sol.averages.get(category, {})
                    row = {"Lösung": emojis[idx] if idx < len(emojis) else f"Lösung {key+1}"}
                    row.update(avg)
                    columns.update(avg.keys())
                    rows.append(row)
                if rows:
                    df_avg = pd.DataFrame(rows)
                    df_avg = df_avg.set_index("Lösung")
                    # Nur die Spalten anzeigen, die auch in dieser Kategorie vorkommen
                    df_avg = df_avg[list(sorted(columns))]
                    st.write(f"**{category.capitalize()}**")
                    st.dataframe(df_avg)

            # Optional: Balkendiagramm für ausgewählte absolute Kennzahlen
            metrics = [
                ("Erreichte Baustellen", "Erreichte Baustellen"),
                ("Erreichte Bestellpositionen", "Erreichte Bestellpositionen"),
                ("Stammfahrerverletzungen", "Stammfahrerverletzungen"),
                ("Baustellenkenntnisverletzungen", "Baustellenkenntnisverletzungen"),
                ("Abweichung Zielstunden", "Abweichung Zielstunden"),
                ("Arbeitswegedistanz (km)", "Arbeitswegedistanz (km)"),
                ("Maschinentransport (km)", "Maschinentransport (km)"),
                ("Genutzte Arbeiter", "Genutzte Arbeiter"),
                ("Genutzte Maschinen", "Genutzte Maschinen"),
            ]
            instanz_values = {
                "Erreichte Baustellen": self.number_sites,
                "Erreichte Bestellpositionen": self.number_shifts,
                "Genutzte Arbeiter": self.number_worker,
                "Genutzte Maschinen": self.number_machines,
            }
            for metric, title in metrics:
                df_compare_numeric = df_compare.reset_index().copy()
                df_compare_numeric[metric] = pd.to_numeric(df_compare_numeric[metric], errors="coerce")
                fig = px.bar(
                df_compare_numeric,
                x="Lösung",
                y=metric,
                title=title,
                color="Lösung",
                color_discrete_sequence=px.colors.qualitative.Plotly
                )
                # Instanzwert als horizontale Linie
                instanz_value = instanz_values.get(metric)
                if pd.api.types.is_number(instanz_value):
                    fig.add_hline(y=instanz_value, line_dash="dash", line_color="black", annotation_text="Instanz", annotation_position="top left")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.plotly_chart(fig, use_container_width=True)
        


    def run(self):

        selected = False
        if not selected:
            # Anzahl Lösungen Button
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
            # Anzahl Lösungen Definition
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


class SolutionData:
    def __init__(self, raw_data: dict, key: int):
        self.key = key
        self.raw = raw_data

        self.worker_assignments = dict()
        self.worker_blocking = dict()
        self.worker_hours = dict()

        for worker, shifts in raw_data.get("Arbeiterloesung", {}).get("Arbeiterzuweisung", {}).items():
            self.worker_assignments[worker] = []
            self.worker_blocking[worker] = []

            for shift in shifts:
                if shift.get("Typ") == "blocking":
                    self.worker_blocking[worker].append(shift)
                else:
                    self.worker_assignments[worker].append(shift)

        self.machine_assignments = dict()
        self.machine_blocking = dict()
        self.machine_hours = dict()

        for machine, usages in raw_data.get("MaschinenLoesung", {}).get("Maschinenzuweisung", {}).items():
            self.machine_assignments[machine] = []
            self.machine_blocking[machine] = []

            for usage in usages:
                if usage.get("Typ") == "blocking":
                    self.machine_blocking[machine].append(usage)
                else:
                    self.machine_assignments[machine].append(usage)


        if include_attachments:
            self.attachment_assignments = dict()
            self.attachment_blocking = dict()
            self.attachment_hours = dict()

            for attachment, usages in raw_data.get("AnbaugeraeteLoesung", {}).get("Anbaugeraetzuweisung", {}).items():
                self.attachment_assignments[attachment] = []
                self.attachment_blocking[attachment] = []

                for usage in usages:
                    if usage.get("Typ") == "blocking":
                        self.attachment_blocking[attachment].append(usage)
                    else:
                        self.attachment_assignments[attachment].append(usage)

                


    def to_dict(self):
        return self.statistics