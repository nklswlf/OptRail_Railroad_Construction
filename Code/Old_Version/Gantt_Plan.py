import json
import pandas as pd
import plotly.express as px
import os


def CreateGanttDiagram(input_file, parent_folder):

    instance = input_file.split('Construction_')[1].split('_reduced')[0]

    # Berechne das Skriptverzeichnis
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Baue die Dateipfade basierend auf dem Skriptverzeichnis
    input_file_path = os.path.join(script_dir, "..", "Data", "Instanzen", parent_folder, input_file)
    output_file_path = os.path.join(script_dir, "..", "Data", "Solution", parent_folder, "Loesung_" + input_file)
    

    

    with open(input_file_path, 'r') as file:
        inputData = json.load(file)
        
    with open(output_file_path, 'r') as file:
        outputData = json.load(file)


    ### Gantt Diagramm - Schichtplan erstellen
    # Daten zu den zugewiesenen Arbeitern aus der Lösung laden
    worker = outputData['Arbeiterzuweisung']
    # Liste für Arbeiter, die keiner Schicht zugewiesen wurden
    not_assigned_worker = list()

    # Überprüfen, ob alle in der Eingabedatei definierten Arbeiter auch zugewiesen sind
    for w in inputData['Arbeiter']:
        if w['Name'] not in worker:
            not_assigned_worker.append(w['Name'])

    # DataFrame erstellen, um die Schichtinformationen der zugewiesenen Arbeiter zu speichern
    df = pd.DataFrame(columns=['Arbeiter', 'Start', 'Ende', 'ID'])
    new_rows = []

    # Daten aus der Lösung zu den Arbeiterschichten im DataFrame speichern
    for w in worker:
        for t in worker[w]:
            new_rows.append({'Arbeiter': w, 'Start': t['Start'], 'Ende': t['Ende'], 'ID': t['ID']})

    # Daten in den DataFrame zusammenfügen
    df = pd.concat([df, pd.DataFrame(new_rows)])

    # Funktion zur Bestimmung des Schichttyps basierend auf der Startzeit
    def shift_type(start):
        hour = pd.to_datetime(start).hour  # Startzeit in Stunde umwandeln
        return 'Frühschicht' if hour < 14 else 'Spätschicht'  # Frühschicht vor 14 Uhr, sonst Spätschicht

    # Schichttyp zur DataFrame hinzufügen
    df['Shift_Type'] = df['Start'].apply(shift_type)

    # Funktion zur Ermittlung der Baustellennummer basierend auf der ID
    def get_instance_id(task_id):
        # Die Baustellennummer wird den Bestellpositionen aus der Eingabedatei entnommen
        for task in inputData['Bestellpositionen']:
            if task['ID'] == task_id:
                return task['Auftragsnummer']
        return None

    # Baustellennummer zur DataFrame hinzufügen
    df['Baustellennummer'] = df['ID'].apply(get_instance_id)


    # Erstellen des Gantt-Diagramms
    fig = px.timeline(df, 
                    x_start="Start", 
                    x_end="Ende", 
                    y="Arbeiter", 
                    color="Shift_Type",
                    hover_data={'Shift_Type': False, 'Baustellennummer': True, 'Start': True, 'Ende': True, 'Arbeiter': False},
                    category_orders={"Arbeiter": sorted(df["Arbeiter"].unique(), key=lambda x: int(x.split("_")[1]), reverse=True)},
                    color_discrete_map={"Frühschicht": "lightblue", "Spätschicht": "lightcoral"})

    # Diagrammlayout aktualisieren
    fig.update_layout(title="Einsatz der Arbeiter mit Baustelleninformationen", 
                    xaxis_title="Datum", 
                    yaxis_title="Arbeiter")


    # Anzeige der Arbeiter ohne zugewiesene Schicht
    print(f"Arbeiter ohne Schicht: {not_assigned_worker}")
    ### Gantt Diagramm - Maschineneinsatzplan erstellen
    # Daten zu den zugewiesenen Maschinen und Anbaugeräte aus der Lösung laden
    machines = outputData['Maschinenzuweisung']
    attachments = outputData['Anbaugeraetzuweisung'] if 'Anbaugeraetzuweisung' in outputData else {}
    # Liste für Maschinen, die keiner Baustelle zugewiesen wurden
    not_assigned_machines = []

    # Überprüfen, ob alle in der Eingabedatei definierten Maschinen auch zugewiesen sind
    for m in inputData['Maschinen']:
        if m['Name'] not in machines:
            not_assigned_machines.append(m['Name'])

    # DataFrames erstellen, um die Einsatzinformationen der zugewiesenen Maschinen und Anbaugeräte zu speichern
    df_machines = pd.DataFrame(columns=['Name', 'Start', 'Ende', 'ID', 'Typ'])
    df_attachments = pd.DataFrame(columns=['Name', 'Start', 'Ende', 'ID', 'Typ'])
    new_machine_rows = []
    new_attachment_rows = []

    # Daten aus der Lösung zu den Maschineneinsätzen im DataFrame speichern
    for m in machines:
        for t in machines[m]:
            new_machine_rows.append({'Name': m, 'Start': t['Start'], 'Ende': t['Ende'], 'ID': t['ID'], 'Typ': 'Maschine'})

    # Daten aus der Lösung zu den Anbaugeräteeinsätzen im DataFrame speichern
    for a in attachments:
        for t in attachments[a]:
            new_attachment_rows.append({'Name': a, 'Start': t['Start'], 'Ende': t['Ende'], 'ID': t['ID'], 'Typ': 'Anbaugerät'})

    # Maschinen- und Anbaugeräte-Daten in einen gemeinsamen DataFrame zusammenfügen
    df_machines = pd.concat([df_machines, pd.DataFrame(new_machine_rows)])
    df_attachments = pd.concat([df_attachments, pd.DataFrame(new_attachment_rows)])
    df_combined = pd.concat([df_machines, df_attachments])

    # Funktion zur Ermittlung der Baustellennummer basierend auf der ID
    def get_instance_id_for_combined(task_id):
        # Die Baustellennummer wird den Bestellpositionen aus der Eingabedatei entnommen
        for task in inputData['Bestellpositionen']:
            if task['ID'] == task_id:
                return task['Auftragsnummer']
        return None

    # Baustellennummer zur DataFrame hinzufügen
    df_combined['Baustellennummer'] = df_combined['ID'].apply(get_instance_id_for_combined)

    # Gantt-Diagramm für Maschinen und Anbaugeräte erstellen, farblich nach Baustellennummer unterschieden
    fig_combined = px.timeline(
        df_combined, 
        x_start="Start", 
        x_end="Ende", 
        y="Name", 
        color="Baustellennummer",  # Farbige Unterscheidung nach Baustellennummer
        hover_data={'Baustellennummer': False, 'Start': True, 'Ende': True, 'Typ': True, 'Name': False},
        category_orders={
            "Name": sorted(df_combined["Name"].unique(), reverse=True),  # Sortierung der Namen
            "Baustellennummer": sorted(df_combined["Baustellennummer"].unique(), key=lambda x: int(x))  # Sortierung der Baustellennummern
        }
    )

    # Diagrammlayout aktualisieren
    fig_combined.update_layout(
        title="Einsatz von Maschinen und Anbaugeräten nach Baustelle", 
        xaxis_title="Datum", 
        yaxis_title="Name"
    )





    # Gantt-Diagramm anzeigen
    fig.show()

    # HTML-Datei speichern, um das Diagramm extern anzuzeigen
    #fig.write_html(html_file_path,"Shift_Plan_"+instance+".html")
    # Pfad für die HTML-Datei berechnen
    # Absoluter Pfad zur HTML-Datei
    html_file_path_shift = os.path.join(script_dir, "..", "Data", "Solution", parent_folder, f"Shift_Plan_{instance}.html")
    
    # Zielordner erstellen, falls nicht vorhanden
    html_folder = os.path.dirname(html_file_path_shift)
    os.makedirs(html_folder, exist_ok=True)

    # HTML-Datei speichern
    fig.write_html(html_file_path_shift)



    html_file_path_machine = os.path.join(script_dir, "..", "Data", "Solution", parent_folder, f"Machine_Plan_{instance}.html")

    # Zielordner erstellen, falls nicht vorhanden
    html_folder = os.path.dirname(html_file_path_machine)
    os.makedirs(html_folder, exist_ok=True)

    # HTML-Datei speichern
    fig_combined.write_html(html_file_path_machine)

    
    # Gantt-Diagramm anzeigen
    fig_combined.show()



    # Anzeige der Maschinen ohne zugewiesene Schicht
    print(f"Maschinen ohne Einsatz: {not_assigned_machines}")