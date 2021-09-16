"""
Parses the PhilipsECG format and writes out the data to a CSV file and saves the 12-lead ECG waveform

Usage: python parse_xml.py <input ECG XML file> <output CSV> <output 12-lead ECG waveform>
Example: python parse_xml.py ecg.xml output.csv output.png
"""

import csv
import ecg_plot
import numpy as np
import sys
from philips import parse

input_file = sys.argv[1]
output_file = sys.argv[2]
output_ecg_waveform_file = sys.argv[3]


#
# Main Code
#

with open(output_file, 'w') as csvfile:
    csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writerow(["date", "time", "dateofbirth", "sex", "mrn", "csn", "meanqrsdur", "meanprint", "heartrate", "rrint", "pdur", "qonset", "tonset", "qtint", "qtcb", "qtcf", "QTcFM", "QTcH", "pfrontaxis", "i40frontaxis", "qrsfrontaxis", "stfrontaxis", "tfrontaxis", "phorizaxis", "i40horizaxis", "t40horizaxis", "qrshorizaxis", "sthorizaxis", "severity", "statements"])

    output_rows, processed_leads = parse(input_file)
    for output_row in output_rows:
        csvwriter.writerow(output_row)
    ecg_plot.plot(np.array(processed_leads), sample_rate=500, title='ECG 12')
    ecg_plot.save_as_png(output_ecg_waveform_file.replace(".png", ""))
