import InputData
import OutputData
import MIP_Flow


# Reduced
#instance_filename = "Construction_a1_o12_m3_an5_ar3_reduced.json"
#instance_filename = "Construction_a3_o80_m10_an10_ar9_reduced.json"
#instance_filename = "Construction_a5_o96_m10_an10_ar10_reduced.json"

# 10 Sites --> "Construction_a10_o118_m6_an53_ar13.json": Instance not duable since one order has no order items
instance_filename = "Construction_a10_o107_m5_an57_ar12.json"
#instance_filename = "Construction_a10_o114_m6_an57_ar11.json"
#instance_filename = "Construction_a10_o119_m5_an54_ar13.json"
#instance_filename = "Construction_a10_o144_m6_an53_ar12.json"

# 15 Sites
#instance_filename = "Construction_a15_o191_m8_an74_ar18.json"

# 20 Sites
#instance_filename = "Construction_a20_o259_m11_an101_ar26.json"

# 50 Sites
#instance_filename = "Construction_a50_o578_m28_an276_ar66.json"



def main():
    data = InputData.InputData(instance_filename)
    optimizer = MIP_Flow.FlowFormulation(data)
    MIP_solution, optimization_strategy = optimizer.execute()

    feasible = MIP_solution.feasibility_check()

    if feasible:
        optimizer.save_solution_to_file()
        #OutputData.GanttDiagramGenerator(data.instance_filename , data._parent_folder, optimization_strategy).create_gantt_diagrams()



if __name__ == "__main__":
    main()









def TestInputData():
    instance_filename = "Construction_a20_o276_m12_an101_ar25.json"

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

    for order in data.orders:
        print(order.order_number)
        print(order.order_item_ids)