"""
Parses the PhilipsECG format and writes out the data to a CSV file and saves the 12-lead ECG waveforms as a single large NumPy array

Usage: python parse_xml_folder.py -i <input ECG XML folder> -o <output CSV> -n <output 12-lead ECG waveforms> -m <output ECG image folder>
Example: python parse_xml_folder.py -i ecgs -o output.csv -n output.npy -m ecg-imgs
"""

import os
import csv
import numpy as np
import pandas as pd
from philips import parse
from concurrent import futures
from tqdm import tqdm
import argparse
from pathlib import Path
import ecg_plot
from datetime import datetime
import time

#
# Main Code
#

def call_parse(args):
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    filename, path, output_image_folder, output_numpy_path = args
    print(f"[{dt_string}] Working on {filename}, {path}")
    try:
        output_rows, leads = parse(path)

        if output_image_folder is not None:
            ecg_plot.plot(np.array(leads), sample_rate=500, title='12-Lead ECG', columns=1)
            ecg_plot.save_as_png(f"{output_image_folder}/{filename.replace('.xml', '')}")

        if leads is None or len(leads.shape) < 2 or leads.shape[0] != 12 or leads.shape[1] != 5500:
            print(f"[{dt_string}] [ERROR] The extracted waveform was not of the expected shape {filename}: {str(e)}")

            return None, None, None
        else:
            return output_rows, leads if output_numpy_path is not None else None, filename
    except Exception as e:
        print(f"[{dt_string}] [ERROR] There was a problem processing {filename}: {str(e)}")
        return None, None, None


def main(args):
    input_folder = args.input_folder
    output_file = args.output_file
    output_numpy = args.output_numpy
    output_image_folder = args.output_image_folder
    max_patients = args.max_patients

    output_file_already_exists = False
    already_processed = set()
    if os.path.exists(output_file):
        df = pd.read_csv(output_file)
        already_processed = set(df["input_file_name"].tolist())
        output_file_already_exists = True

    if output_image_folder is not None:
        Path(output_image_folder).mkdir(parents=True, exist_ok=True)

    with open(output_file, 'a') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if not output_file_already_exists:
            csvwriter.writerow(["input_file_name", "date", "time", "dateofbirth", "sex", "mrn", "csn", "meanqrsdur", "meanprint", "heartrate", "rrint", "pdur", "qonset", "qrsdur", "tonset", "qtint", "qtcb", "qtcf", "QTcFM", "QTcH", "pfrontaxis", "i40frontaxis", "qrsfrontaxis", "stfrontaxis", "tfrontaxis", "phorizaxis", "i40horizaxis", "t40horizaxis", "qrshorizaxis", "sthorizaxis", "severity", "statements"])

        fs = []
        with futures.ThreadPoolExecutor(16) as executor:
            for filename in os.listdir(input_folder):
                if filename.endswith(".xml"):
                    if filename in already_processed:
                        print(f"Skipping filename as it already exists...")
                    else:
                        future = executor.submit(call_parse, [filename, os.path.join(input_folder, filename), output_image_folder, output_numpy])
                        fs.append(future)
                        if max_patients is not None and len(fs) >= int(max_patients):
                            break

            overall_processed_leads = []
            for future in futures.as_completed(fs):
                output_rows, processed_leads, filename = future.result(timeout=60)
                if filename is not None and len(output_rows) > 0:
                    csvwriter.writerow([filename] + output_rows[0])
                    if output_numpy is not None:
                        overall_processed_leads.append(processed_leads)
            if output_numpy is not None:
                np.save(output_numpy, np.array(overall_processed_leads))
    print(f"Completed")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parses the PhilipsECG format and writes out the data to a CSV file and saves the 12-lead ECG waveforms as a single large NumPy array')
    parser.add_argument('-i', '--input-folder',
                        required=True,
                        help='ECG XML folder')
    parser.add_argument('-o', '--output-file',
                        required=True,
                        help='The path to the output summary file')
    parser.add_argument('-n', '--output-numpy',
                        required=False,
                        help='The path to the output NumPy file')
    parser.add_argument('-m', '--output-image-folder',
                        required=False,
                        help='The path to the output PNG folder')
    parser.add_argument('-p', '--max-patients',
                        required=False,
                        help='The maximum number of patients to process')

    args = parser.parse_args()

    main(args)

