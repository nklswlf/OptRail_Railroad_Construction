import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import datetime as dt

# Titel der App
st.title("Gantt-Diagramm Visualisierung mit Instanzverwaltung")

# Basisordner für Instanzdateien
instance_folder = "./Instanzen"
os.makedirs(instance_folder, exist_ok=True)  # Ordner erstellen, falls nicht vorhanden

# Datei-Upload der Solution-Datei - streng nach Namenskonvention
uploaded_solution = st.file_uploader("Lade die Solution-Datei hoch (JSON, z. B. Solution_Construction_a10_o107_m5_an57_ar12.json)", type=["json"])



def find_instance_file(instance_folder, instance_name):
    """
    Sucht rekursiv nach einer Instanzdatei in allen Unterordnern.
    """
    for root, _, files in os.walk(instance_folder):
        if instance_name in files:
            return os.path.join(root, instance_name)
    return None


if uploaded_solution is not None:
    solution_name = uploaded_solution.name
    solution_data = json.load(uploaded_solution)

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
                'Shift_Type': 'Early Shift' if pd.to_datetime(shift['Start']).hour < 14 else 'Late Shift'
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

        # Gantt-Diagramm für Arbeiter erstellen
        fig_worker = px.timeline(
            df_worker,
            x_start="Start",
            x_end="Ende",
            y="Arbeiter",
            color="Shift_Type",
            title="Arbeiterzuweisungen (Schichten)",
            color_discrete_map={"Early Shift": "lightblue", "Late Shift": "lightcoral"}
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
        st.plotly_chart(fig_worker)

        # --- Gantt-Diagramm: Maschinen ---
        st.subheader("Gantt-Diagramm: Maschinen")
        machine_assignments = solution_data['Maschinenzuweisung']

        machine_rows = [
            {
                'Maschine': machine,
                'Start': usage['Start'],
                'Ende': usage['Ende'],
                'Baustelle': usage['Auftragsnummer']
            }
            for machine, usages in machine_assignments.items() for usage in usages
        ]
        df_machine = pd.DataFrame(machine_rows)

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
        st.plotly_chart(fig_machine)

        # --- Statistische Kennzahlen ---
        st.subheader("Auswertung")

        # Rechenzeit in Minuten
        rechenzeit_minuten = solution_data["RechenzeitInSekunden"] / 60

        # Erreichte Baustellen (%)
        max_baustellen = solution_data["Baustellenanzahl"]
        fertige_baustellen = solution_data["Baustellenfertig"]
        baustellen_prozent = (fertige_baustellen / max_baustellen) * 100

        # Erreichte Order Items (%)
        max_order_items = solution_data["OrderItemsanzahl"]
        fertige_order_items = solution_data["OrderItemsfertig"]
        order_items_prozent = (fertige_order_items / max_order_items) * 100

        # Order Items welche von nicht regulären Arbeitern bearbeitet wurden
        non_regular_driver = solution_data["NichtregulaereFahrer"]
        non_regular_driver_prozent = (non_regular_driver / max_order_items) * 100

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

        # Arbeitswege der Arbeiter
        arbeitswege = solution_data["ArbeitswegGesamt"]

        # Arbeitszeiten
        arbeitszeiten = solution_data["Arbeitszeit"]
        not_used_worker = [key for key, value in arbeitszeiten.items() if value == 0]
        arbeitszeiten = {key: value for key, value in arbeitszeiten.items() if value != 0}


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



        # Anzeige der statistischen Kennzahlen
        st.write(f"**Rechenzeit:** {rechenzeit_minuten:.1f} Minuten")
        st.write("")
        st.write(f"**Erreichte Baustellen:** {fertige_baustellen} von {max_baustellen} ➡️ {baustellen_prozent:.1f}%")
        st.write(f"**Erreichte Order Items:** {fertige_order_items} von {max_order_items} ➡️ {order_items_prozent:.1f}%")
        st.dataframe(df_baustellen)
        st.write("")
        st.write(f"**Anzahl Stammfahrerverletzungen:** {non_regular_driver} von {max_order_items} ➡️ {non_regular_driver_prozent:.1f}%")
        st.write("")
        st.write(f"**Gesamttransportdistanz:** {transportdistanz_gesamt:.1f} km")
        st.write(f"**Gesamtarbeitsweg:** {arbeitswege:.1f} km")        
        st.write("")
        st.write(f"**Anteil genutzter Maschinen:** {maschinen_genutzt} von {maschinen_gesamt} ➡️ {maschinen_prozent:.1f}%")
        st.write(f"**Anteil genutzter Arbeiter:** {arbeiter_genutzt} von {arbeiter_gesamt} ➡️ {arbeiter_prozent:.1f}%")        
        st.write("")

        # Arbeitszeiten-Tabelle anzeigen
        df_arbeitszeiten = pd.DataFrame.from_dict(arbeitszeiten, orient='index', columns=['Gesamtstunden'])
        df_arbeitszeiten.index.name = 'Arbeiter_ID'
        df_arbeitszeiten['Auslastung'] = ((df_arbeitszeiten['Gesamtstunden'] / 160) * 100).round(1).astype(str) + '%'
        st.write("**Arbeitszeit pro Arbeiter:**")
        st.dataframe(df_arbeitszeiten)
        st.write(f"➡️ **Nicht genutzte Arbeiter:** {', '.join(not_used_worker)}")

        