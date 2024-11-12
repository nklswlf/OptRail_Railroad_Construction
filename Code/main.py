from InputData import InputData

def TestInputData():
    # Ersetzen Sie "instance.json" durch den Namen Ihrer JSON-Datei
    instance_filename = "AnzahlAuftraege_NEW_10/Construction_a10_o107_m5_an57_ar12.json"

    # Erstellen einer InputData-Instanz
    data = InputData(instance_filename)
    
    # Anzeigen der geladenen Daten mit strukturierten Ausgaben
    print("\nOrders:")
    for order in data.orders:
        print(order)

    print("\nOrder Items:")
    for item in data.order_items:
        print(item)

    print("\nAttachments:")
    for attachment in data.attachments:
        print(attachment)

    print("\nWorkers:")
    for worker in data.workers:
        print(worker)

    print("\nMachines:")
    for machine in data.machines:
        print(machine)

    # Anzeigen der Instanz-Metadaten
    print("\nStart Date:", data.start_date)
    print("End Date:", data.end_date)
    print("Contains Durations:", data.contains_durations)

    # Anzeigen der Transport- und Arbeitswege
    print("\nTransport Routes:")
    for row in data.transport_routes:
        print(row)

    print("\nWork Routes:")
    for row in data.work_routes:
        print(row)

if __name__ == "__main__":
    TestInputData()