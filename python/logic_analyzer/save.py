import csv

def save_binary(filename, data: bytes):
    with open(filename, "wb") as f:
        f.write(data)

def save_digital_csv(filename, samples):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sample", "value"])
        for i, v in enumerate(samples):
            writer.writerow([i, v])

def save_analog_csv(filename, samples):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sample", "adc_raw"])
        for i, (v,) in enumerate(samples):
            writer.writerow([i, v])