"""
Parses the PhilipsECG format and writes out the data to a CSV file and saves the 12-lead ECG waveform

Usage: python parse_xml.py <input ECG XML file> <output CSV> <output 12-lead ECG waveform>
Example: python parse_xml.py ecg.xml output.csv output.png
"""

import csv
import ecg_plot
import xml.etree.ElementTree as ET
import base64
import numpy as np
import sys

# Reads file from input
from philips import read_chunk, create_from_lead_set
from waveform_utils import apply_filter, normalize

input_file = sys.argv[1]
output_file = sys.argv[2]
output_ecg_waveform_file = sys.argv[3]


#
# Main Code
#

def get_global_measurement(globalmeasurements, attr):
    elems = globalmeasurements.findall(attr)
    if len(elems) > 0:
        return globalmeasurements.findall(attr)[0].text
    else:
        return ""

it = ET.iterparse(input_file)
for _, el in it:
    prefix, has_namespace, postfix = el.tag.partition('}')
    if has_namespace:
        el.tag = postfix
root = it.root


with open(output_file, 'w') as csvfile:
    csvwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csvwriter.writerow(["date", "time", "heartrate", "rrint", "pdur", "qonset", "tonset", "qtint", "qtcb", "qtcf", "QTcFM", "QTcH", "pfrontaxis", "i40frontaxis", "qrsfrontaxis", "stfrontaxis", "tfrontaxis", "phorizaxis", "i40horizaxis", "t40horizaxis", "qrshorizaxis", "sthorizaxis", "severity", "statements"])

    # Parse out all elements
    #
    reportinfo = root.findall('reportinfo')[0]
    report_date = reportinfo.attrib["date"]
    report_time = reportinfo.attrib["time"]

    interpretations = root.findall('interpretations')[0]
    for interpretation in interpretations.findall('interpretation'):
        globalmeasurements = interpretation.findall('globalmeasurements')[0]
        heartrate = get_global_measurement(globalmeasurements, 'heartrate')
        rrint = get_global_measurement(globalmeasurements, 'rrint')
        pdur = get_global_measurement(globalmeasurements, 'pdur')
        qonset = get_global_measurement(globalmeasurements, 'qonset')
        qrsdur = get_global_measurement(globalmeasurements, 'qrsdur')
        tonset = get_global_measurement(globalmeasurements, 'tonset')
        qtint = get_global_measurement(globalmeasurements, 'qtint')
        qtcb = get_global_measurement(globalmeasurements, 'qtcb')
        qtcf = get_global_measurement(globalmeasurements, 'qtcf')
        QTcFm = ""
        QTcH = ""
        for qtco in globalmeasurements.findall('qtco'):
            if qtco.attrib["label"] == 'QTcFm':
                QTcFm = qtco.text
            elif qtco.attrib["label"] == 'QTcH':
                QTcH = qtco.text
        pfrontaxis = get_global_measurement(globalmeasurements, 'pfrontaxis')
        i40frontaxis = get_global_measurement(globalmeasurements, 'i40frontaxis')
        qrsfrontaxis = get_global_measurement(globalmeasurements, 'qrsfrontaxis')
        stfrontaxis = get_global_measurement(globalmeasurements, 'stfrontaxis')
        tfrontaxis = get_global_measurement(globalmeasurements, 'tfrontaxis')
        phorizaxis = get_global_measurement(globalmeasurements, 'phorizaxis')
        i40horizaxis = get_global_measurement(globalmeasurements, 'i40horizaxis')
        t40horizaxis = get_global_measurement(globalmeasurements, 't40horizaxis')
        qrshorizaxis = get_global_measurement(globalmeasurements, 'qrshorizaxis')
        sthorizaxis = get_global_measurement(globalmeasurements, 'sthorizaxis')
        severity = interpretation.findall('severity')[0].text.replace("-", "").strip()
        statements = interpretation.findall('statement')
        leftstatements = []
        for statement in statements:
            leftstatement = statement.findall('leftstatement')[0].text
            leftstatements.append(leftstatement)
        
        csvwriter.writerow([report_date, report_time, heartrate, rrint, pdur, qonset, tonset, qtint, qtcb, qtcf, QTcFm, QTcH, pfrontaxis, i40frontaxis, qrsfrontaxis, stfrontaxis, tfrontaxis, phorizaxis, i40horizaxis, t40horizaxis, qrshorizaxis, sthorizaxis, severity, ",".join(leftstatements)])

    waveforms = root.findall("waveforms")[0]
    waveform = waveforms.findall("parsedwaveforms")[0].text.replace("\n", "")
    content_str = waveform.strip()

    content = base64.b64decode(content_str)
    decoded_arr = []
    offset = 0
    i = 0
    while True:
        offset, decoded = read_chunk(content, offset)
        if offset is None:
            break
        decoded_arr.append(decoded)
        i += 1
    leads = create_from_lead_set(decoded_arr)

    processed_leads = []
    for lead in leads:
        lead = apply_filter(np.array(lead))
        lead = normalize(lead)
        processed_leads.append(lead)

    ecg_plot.plot(np.array(processed_leads), sample_rate=500, title='ECG 12')
    ecg_plot.save_as_png(output_ecg_waveform_file.replace(".png", ""))
