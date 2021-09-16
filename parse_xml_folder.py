"""
Parses the PhilipsECG format and writes out the data to a CSV file and saves the 12-lead ECG waveforms as a single large NumPy array

Usage: python parse_xml_folder.py <input ECG XML folder> <output CSV> <output 12-lead ECG waveforms>
Example: python parse_xml_folder.py ecgs output.csv output.npy
"""

import os
import csv
import numpy as np
import sys
from philips import parse
from concurrent import futures
from tqdm import tqdm

input_folder = sys.argv[1]
output_file = sys.argv[2]
output_ecg_waveform_file = sys.argv[3]


#
# Main Code
#

def call_parse(args):
    filename, path = args
    output_rows, leads = parse(path)
    return output_rows, leads, filename

def main():
    with open(output_file, 'w') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvwriter.writerow(["input_file_name", "date", "time", "dateofbirth", "sex", "mrn", "csn", "meanqrsdur", "meanprint", "heartrate", "rrint", "pdur", "qonset", "tonset", "qtint", "qtcb", "qtcf", "QTcFM", "QTcH", "pfrontaxis", "i40frontaxis", "qrsfrontaxis", "stfrontaxis", "tfrontaxis", "phorizaxis", "i40horizaxis", "t40horizaxis", "qrshorizaxis", "sthorizaxis", "severity", "statements"])

        fs = []
        with futures.ProcessPoolExecutor(16) as executor:
            for filename in os.listdir(input_folder):
                if filename.endswith(".xml"):
                    future = executor.submit(call_parse, [filename, os.path.join(input_folder, filename)])
                    fs.append(future)

            overall_processed_leads = []
            for future in tqdm(futures.as_completed(fs), total=len(fs)):
                output_rows, processed_leads, filename = future.result(timeout=60)
                for output_row in output_rows:
                    csvwriter.writerow([filename] + output_row)
                overall_processed_leads.append(processed_leads)

            np.save(output_ecg_waveform_file, np.array(overall_processed_leads))


if __name__ == '__main__':
    main()