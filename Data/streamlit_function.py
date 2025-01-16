import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import datetime as dt



def upload_solution(key, instance = None):
    # File upload for the Solution file
    uploaded_solution = st.file_uploader(
        "Upload the Solution file (JSON, e.g., Solution_Construction_a10_o107_m5_an57_ar12.json)", 
        type=["json"], 
        key=f"solution_uploader_{key}"
    )

    solution_data = None
    instance_name = None


    if uploaded_solution:
        instance_name = uploaded_solution.name
        instance_name = instance_name.replace("Solution_Construciton", "")
        instance_name = instance_name.replace(".json", "")
        if uploaded_solution.name.startswith("Solution_Construction") and instance is None or instance == instance_name:
            st.success("Solution file uploaded successfully!")
            solution_data = json.load(uploaded_solution)
        else:
            st.error("Invalid file name. Please upload a Solution that matches the instance and starts with 'Solution_Construction'.")

    


    
    return uploaded_solution, solution_data, instance_name

        




def streamlit(key, uploaded_solution, solution_data):

    # Basisordner relativ zum Skript
    instance_folder = os.path.join(os.path.dirname(__file__), "Instanzen")

    # Funktion zum Finden der Instanzdatei
    def find_instance_file(instance_folder, instance_name):
        """
        Sucht rekursiv nach einer Instanzdatei in allen Unterordnern.
        """
        if not os.path.exists(instance_folder):
            st.error(f"❌ Der Ordner '{instance_folder}' wurde nicht gefunden.")
            return None

        # Rekursive Suche nach der Datei
        for root, _, files in os.walk(instance_folder):
            if instance_name in files:
                return os.path.join(root, instance_name)

        st.warning(f"❌ Die Datei '{instance_name}' wurde nicht gefunden.")
        return None
    
    results = dict()



    if uploaded_solution is not None and solution_data is not None:
        solution_name = uploaded_solution.name

        # Instanzdateiname ableiten
        instance_name = solution_name.replace("Solution_", "")
        instance_path = find_instance_file(instance_folder, instance_name)

        instance_data = None
        if instance_path:
            with open(instance_path, 'r') as file:
                instance_data = json.load(file)
            st.success(f"Passende Instanzdatei wurde gefunden: {instance_name}")
        else:
            st.warning("Passende Instanzdatei konnte nicht gefunden werden.")
            uploaded_instance = st.file_uploader(f"Lade die passende Instanz-Datei hoch (erwartet: {instance_name}):", type=["json"])

            if uploaded_instance is not None:
                if uploaded_instance.name == instance_name:
                    instance_data = json.load(uploaded_instance)
                    save_path = os.path.join(instance_folder, instance_name)
                    with open(save_path, 'w') as file:
                        json.dump(instance_data, file, indent=4)
                    st.success(f"Instanzdatei wurde gespeichert: {instance_name}")
                else:
                    st.error(f"Ungültiger Dateiname. Erwartet wurde: {instance_name}")

        if instance_data is not None:
            # --- Gantt-Diagramm: Arbeiter ---
            st.subheader("Gantt-Diagramm: Arbeiter")
            worker_assignments = solution_data['Arbeiterzuweisung']

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

            # Arbeiter sortieren
            df_worker['Arbeiter'] = pd.Categorical(
                df_worker['Arbeiter'],
                categories=sorted(df_worker['Arbeiter'].unique(), key=lambda x: int(x.split('_')[1])),
                ordered=True
            )

            # Anzahl verschiedener Baustellen pro Arbeiter zählen und als dictionary speichern
            arbeiter_anzahl_baustellen_dict = (
                df_worker.groupby('Arbeiter')['Baustelle']
                .nunique()
                .to_dict()
            )

            # Präfix 'Arbeiter_' entfernen und Zahlen als Keys verwenden
            arbeiter_anzahl_baustellen_dict = {str(worker.split('_')[1]): sites for worker, sites in arbeiter_anzahl_baustellen_dict.items()}   



            # Anzahl der Schichten pro Arbeiter und Schichttyp zählen und direkt in ein Dictionary umwandeln
            arbeiter_schicht_dict = (
                df_worker.groupby(['Arbeiter', 'Schichttyp'])
                .size()
                .unstack(fill_value=0)
                .rename_axis(None, axis=1)
                .to_dict(orient='index')
            )

            # Präfix 'Arbeiter_' entfernen und Zahlen als Keys verwenden
            arbeiter_schicht_dict = {str(worker.split('_')[1]): shifts for worker, shifts in arbeiter_schicht_dict.items()}


            # Gantt-Diagramm für Arbeiter erstellen
            fig_worker = px.timeline(
                df_worker,
                x_start="Start",
                x_end="Ende",
                y="Arbeiter",
                color="Schichttyp",
                title="Arbeiterzuweisungen (Schichten)",
                color_discrete_map={"Frühschicht": "lightblue", "Spätschicht": "lightcoral"},

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
            st.plotly_chart(fig_worker, key= f"worker_gantt_{key}")

            # --- Gantt-Diagramm: Maschinen ---
            st.subheader("Gantt-Diagramm: Maschinen")
            machine_assignments = solution_data['Maschinenzuweisung']

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
            df_machine = pd.DataFrame(machine_rows)

            # Stunden in Nutzung
            stunden_in_nutzung_dict = (
                df_machine.groupby('Maschine')['Dauer']
                .sum()
                .to_dict()
            )
            
            tage_in_nutzung_dict = {k: v / 24 for k, v in stunden_in_nutzung_dict.items()}

            maschinen_anzahl_baustellen_dict = (
                df_machine.groupby('Maschine')['Baustelle']
                .nunique()
                .to_dict()
            )

            # Baustellen sortieren
            unique_sites = sorted(df_machine['Baustelle'].unique(), key=lambda x: int(x))
            color_map = {site: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i, site in enumerate(unique_sites)}

            # Gantt-Diagramm für Maschinen erstellen
            fig_machine = px.timeline(
                df_machine,
                x_start="Start",
                x_end="Ende",
                y="Maschine",
                color="Baustelle",
                title="Maschinen- und Anbaugerätezuweisungen nach Baustelle",
                color_discrete_map=color_map,
                category_orders={"Baustelle": unique_sites}
            )

            # Wochenenden hervorheben
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
            st.plotly_chart(fig_machine, key= f"machine_gantt_{key}")

            # --- Statistische Kennzahlen ---

            # Rechenzeit in Minuten
            rechenzeit_minuten = solution_data["RechenzeitInSekunden"] / 60

            # Erreichte Baustellen (%)
            max_baustellen = solution_data["Baustellenanzahl"]
            fertige_baustellen = solution_data["Baustellenfertig"]
            baustellen_prozent = (fertige_baustellen / max_baustellen) * 100

            # Erreichte Bestellpositionen (%)
            max_order_items = solution_data["OrderItemsanzahl"]
            fertige_order_items = solution_data["OrderItemsfertig"]
            order_items_prozent = (fertige_order_items / max_order_items) * 100

            # Bestellpositionen welche von nicht regulären Arbeitern bearbeitet wurden
            non_regular_driver = solution_data["NichtregulaereFahrer"]
            non_regular_driver_prozent = (non_regular_driver / fertige_order_items) * 100

            # Anteil genutzter Maschinen
            maschinen_gesamt = solution_data["MaschinenanzahlGesamt"]
            maschinen_genutzt = solution_data["MaschinenGenutzt"]
            maschinen_prozent = (maschinen_genutzt / maschinen_gesamt) * 100

            # Anteil genutzter Arbeiter
            arbeiter_genutzt = len(worker_assignments)
            arbeiter_gesamt = solution_data["ArbeiteranzahlGesamt"]
            arbeiter_prozent = (arbeiter_genutzt / arbeiter_gesamt) * 100

            # Gesamttransportdistanz der Maschinen
            transportdistanz_gesamt = solution_data["TransportdistanzGesamt"]

            # Nicht genutzte Maschinen
            nicht_genutzte_maschinen = list()
            for machine in solution_data["MaschinenGenutztDetails"]:
                if not solution_data["MaschinenGenutztDetails"][machine]:
                    nicht_genutzte_maschinen.append(machine)


            # Arbeitswege der Arbeiter
            arbeitswege = solution_data["ArbeitswegGesamt"]
            arbeitsweg = solution_data["Arbeitsweg"]

            # Arbeitszeiten
            arbeitszeiten = solution_data["Arbeitszeit"]
            not_used_worker = [key for key, value in arbeitszeiten.items() if value == 0]
            arbeitszeiten = {key: value for key, value in arbeitszeiten.items() if value != 0}

            # Tage in Nutzung (Maschinen)
            stunden_in_nutzung = solution_data["Maschinenzuweisung"]




            # --- Tabelle: Anzahl der Bestellpositionen pro Baustelle mit dezenter farblicher Markierung ---
            # Daten aus der Instanzdatei und der Solution-Datei extrahieren
            baustellen_info = instance_data["Auftraege"]
            baustellen_status = solution_data["Baustellebearbeitet"]

            # Tabelle erstellen
            baustellen_rows = []
            for auftrag in baustellen_info:
                baustellen_nummer = auftrag["Baustellennummer"]
                bestellpositionen_anzahl = len(auftrag["BestellpositionenStrings"])
                status = baustellen_status[str(baustellen_nummer)]

                baustellen_rows.append({
                    "Baustelle": baustellen_nummer,
                    "Bestellpositionen": bestellpositionen_anzahl,
                    "Status": "✅" if status else "❌"
                })
                

            # DataFrame erstellen
            df_baustellen = pd.DataFrame(baustellen_rows)
            # Index entfernen
            df_baustellen = df_baustellen.set_index("Baustelle")


            st.write("")
            st.write("#### Baustellen und Bestellpositionen")
            st.write(f"**Erreichte Baustellen:** {fertige_baustellen} von {max_baustellen} ➡️ {baustellen_prozent:.1f}%")
            st.write(f"**Erreichte Bestellpositionen:** {fertige_order_items} von {max_order_items} ➡️ {order_items_prozent:.1f}%")
            st.write(f"**Anzahl Stammfahrerverletzungen:** {non_regular_driver} von {fertige_order_items} ➡️ {non_regular_driver_prozent:.1f}%")
            st.dataframe(df_baustellen)


            # Sort the DataFrame by 'Bestellpositionen'
            df_baustellen_sorted = df_baustellen.reset_index().sort_values(by="Bestellpositionen", ascending=True)

            # Add a new column for a generic X-axis label (e.g., "Site 1", "Site 2")
            df_baustellen_sorted['Baustelle_Index'] = range(1, len(df_baustellen_sorted) + 1)

            # Define colors for the status
            farben = {
                "✅": "green",
                "❌": "red"
            }

            # Create the bar chart
            fig = px.bar(
                df_baustellen_sorted,
                x="Baustelle_Index",
                y="Bestellpositionen",
                color="Status",
                title="Baustellen-Bestellpositionen",
                color_discrete_map=farben,
                hover_data={"Baustelle": True, "Baustelle_Index": False}
            )

            # Update X-axis to hide labels
            fig.update_layout(
                xaxis_title="",
                xaxis_showticklabels=False
            )

            # Display the chart in Streamlit
            st.plotly_chart(fig, key=f"baustellen_chart_{key}")

            st.write("")
            st.write("#### Maschinen")
            st.write(f"**Anteil eingeplanter Maschinen:** {maschinen_genutzt} von {maschinen_gesamt} ➡️ {maschinen_prozent:.1f}%")
            st.write(f"**Gesamttransportdistanz:** {transportdistanz_gesamt:.1f} km")
            df_maschinenzeiten = pd.DataFrame.from_dict(stunden_in_nutzung_dict, orient='index', columns=['Gesamtstunden'])
            df_maschinenzeiten.index.name = 'Maschine_ID'
            df_maschinenzeiten['Auslastung'] = ((df_maschinenzeiten['Gesamtstunden'] / ((24-2)*31) * 100).round(1).astype(str) + '%')
            df_maschinenzeiten['Tage in Nutzung'] = [round(tage_in_nutzung_dict.get(k, 0), 0) for k in df_maschinenzeiten.index]
            df_maschinenzeiten['Baustellen'] = [maschinen_anzahl_baustellen_dict.get(k, 0) for k in df_maschinenzeiten.index]
            df_maschinenzeiten['Transportdistanz'] = df_maschinenzeiten.index.map(lambda machine: round(solution_data["Transportdistanz"].get(machine, 0), 1))
            st.dataframe(df_maschinenzeiten)
            st.write(f"➡️ **Anzahl nicht eingesetzter Maschinen:** {len(nicht_genutzte_maschinen)}")
            st.write(f"➡️ **IDs nicht eingesetzter Maschinen:** {', '.join(nicht_genutzte_maschinen)}")





            st.write("")
            st.write("#### Arbeiter")
            st.write(f"**Anteil eingeplanter Arbeiter:** {arbeiter_genutzt} von {arbeiter_gesamt} ➡️ {arbeiter_prozent:.1f}%") 
            st.write(f"**Gesamtarbeitsweg:** {arbeitswege:.1f} km")   

            # Arbeitszeiten-Tabelle anzeigen
            df_arbeitszeiten = pd.DataFrame.from_dict(arbeitszeiten, orient='index', columns=['Gesamtstunden'])
            df_arbeitszeiten.index.name = 'Arbeiter_ID'
            df_arbeitszeiten['Auslastung'] = ((df_arbeitszeiten['Gesamtstunden'] / 160) * 100).round(1).astype(str) + '%'
            df_arbeitszeiten['Frühschichten'] = [arbeiter_schicht_dict.get(k, {}).get('Frühschicht', 0) for k in df_arbeitszeiten.index]
            df_arbeitszeiten['Spätschichten'] = [arbeiter_schicht_dict.get(k, {}).get('Spätschicht', 0) for k in df_arbeitszeiten.index]
            df_arbeitszeiten['Baustellen'] = [arbeiter_anzahl_baustellen_dict.get(k, 0) for k in df_arbeitszeiten.index]
            df_arbeitszeiten['Arbeitsweg'] = df_arbeitszeiten.index.map(lambda worker: round(solution_data["Arbeitsweg"].get(worker, 0), 1))
            st.dataframe(df_arbeitszeiten)
            st.write(f"➡️ **Anzahl nicht eingesetzter Arbeiter:** {len(not_used_worker)}")
            st.write(f"➡️ **IDs nicht eingesetzter Arbeiter:** {', '.join(not_used_worker)}")

            # Histogramm erstellen
            fig = px.histogram(
                df_arbeitszeiten,
                x='Gesamtstunden',
                nbins=8,
                title="Auslastungsverteilung der Arbeitszeiten",
                labels={'Gesamtstunden': 'Arbeitsstunden'},
                histnorm='percent',  # Prozentuale Darstellung auf der Y-Achse
                range_x=[0, 160],
                color_discrete_sequence=['#636EFA']
            )

            # Tooltip anpassen: Label ändern und Werte runden
            fig.update_traces(
                hovertemplate="<b>Arbeitsstunden:</b> %{x}<br><b>Anteil Arbeiter:</b> %{y:.1f}%<extra></extra>"
            )
            # vertikale rote dashen Linie hinzufügen bis zu maximalen y-Wert
            fig.add_vline(x=140, line_dash="dash", line_color="red")

            
            # Y-Achsen-Label hinzufügen
            fig.update_layout(
                yaxis_title='Anteil der eingesetzten Arbeiter (%)',
                bargap=0.1
            )

            # Diagramm in Streamlit anzeigen
            st.plotly_chart(fig, key=f"arbeitszeiten_histogram_{key}")


            st.write("#### Weitere Informationen")
            # Anzeige der statistischen Kennzahlen
            st.write(f"**Rechenzeit:** {rechenzeit_minuten:.1f} Minuten")

        
        results["Baustellen"] = fertige_baustellen
        results["OrderItems"] = fertige_order_items
        results["NonRegularDriver"] = non_regular_driver
        results["Maschinen"] = maschinen_genutzt
        results["Arbeiter"] = arbeiter_genutzt
        results["Transportdistanz"] = transportdistanz_gesamt
        results["Arbeitsweg"] = arbeitswege
        results["Rechenzeit"] = rechenzeit_minuten


        
        return results
    


import streamlit as st
import pandas as pd
import plotly.express as px

def compare_results(results_1=None, results_2=None, results_3=None, results_4=None, results_5=None):
    """
    Vergleicht die absoluten Werte der Ergebnisse und erstellt einzelne Balkendiagramme pro Kennzahl.
    """
    # Ergebnisse in eine Liste umwandeln
    results = [results_1, results_2, results_3, results_4, results_5]
    labels = ["Lösung 1", "Lösung 2", "Lösung 3", "Lösung 4", "Lösung 5"]

    # Nur vorhandene Ergebnisse berücksichtigen
    valid_results = [(label, result) for label, result in zip(labels, results) if result is not None]

    if len(valid_results) < 2:
        st.write("Bitte mindestens zwei Lösungen hochladen, um einen Vergleich durchzuführen.")
        return

    st.write("#### Ergebnisvergleich")

    # DataFrame erstellen
    df_results = pd.DataFrame(
        [result for _, result in valid_results],
        index=[label for label, _ in valid_results]
    )

    # Ergebnisse runden und anzeigen
    df_results = df_results.round(1)
    st.dataframe(df_results)

    # Für jede Kennzahl ein eigenes Balkendiagramm erstellen
    st.write("#### Balkendiagramme für die absoluten Werte der einzelnen Kennzahlen")
    for col in df_results.columns:
        if col == "Rechenzeit":
            label = "Minuten"
        elif col == "Transportdistanz" or col == "Arbeitsweg":
            label = "Distanz (km)"
        else:
            label = "Anzahl"
        fig = px.bar(
            df_results,
            x=df_results.index,
            y=col,
            title=f"{col}",
            labels={"x": "Lösung", col: label},
            color=df_results.index
        )
        st.plotly_chart(fig)