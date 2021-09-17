"""
Parses the PhilipsECG format and writes out the data to a CSV file and saves the 12-lead ECG waveforms as a single large NumPy array

Usage: python parse_xml_folder.py -i <input ECG XML folder> -o <output CSV> -n <output 12-lead ECG waveforms> -m <output ECG image folder>
Example: python parse_xml_folder.py -i ecgs -o output.csv -n output.npy -m ecg-imgs
"""

import os
import csv
import numpy as np
from philips import parse
from concurrent import futures
from tqdm import tqdm
import argparse
from pathlib import Path
import ecg_plot

#
# Main Code
#

def call_parse(args):
    filename, path, output_image_folder = args
    output_rows, leads = parse(path)

    if output_image_folder is not None:
        ecg_plot.plot(np.array(leads), sample_rate=500, title='12-Lead ECG', columns=1)
        ecg_plot.save_as_png(f"{output_image_folder}/{filename.replace('.xml', '')}")

    return output_rows, leads, filename

def main(args):
    input_folder = args.input_folder
    output_file = args.output_file
    output_numpy = args.output_numpy
    output_image_folder = args.output_image_folder

    if output_image_folder is not None:
        Path(output_image_folder).mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(["input_file_name", "date", "time", "dateofbirth", "sex", "mrn", "csn", "meanqrsdur", "meanprint", "heartrate", "rrint", "pdur", "qonset", "tonset", "qtint", "qtcb", "qtcf", "QTcFM", "QTcH", "pfrontaxis", "i40frontaxis", "qrsfrontaxis", "stfrontaxis", "tfrontaxis", "phorizaxis", "i40horizaxis", "t40horizaxis", "qrshorizaxis", "sthorizaxis", "severity", "statements"])

        fs = []
        with futures.ProcessPoolExecutor(4) as executor:
            for filename in os.listdir(input_folder):
                if filename.endswith(".xml"):
                    future = executor.submit(call_parse, [filename, os.path.join(input_folder, filename), output_image_folder])
                    fs.append(future)

            overall_processed_leads = []
            for future in tqdm(futures.as_completed(fs), total=len(fs)):
                output_rows, processed_leads, filename = future.result(timeout=60)
                for output_row in output_rows:
                    csvwriter.writerow([filename] + output_row)

                if output_numpy is not None:
                    overall_processed_leads.append(processed_leads)

            if output_numpy is not None:
                np.save(output_numpy, np.array(overall_processed_leads))


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

    args = parser.parse_args()

    main(args)
