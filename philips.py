"""
Utility functions to parse the Philips ECG XML file.

Methods are based on the Java methods found at:
- https://github.com/sixlettervariables/sierra-ecg-tools/blob/master/jsierraecg/src/org/sierraecg/codecs/XliDecompressor.java
- https://github.com/sixlettervariables/sierra-ecg-tools/blob/master/jsierraecg/src/org/sierraecg/DecodedLead.java

"""

import ctypes
import struct
import numpy as np
from lzw import Lzw
from pathlib import Path
import xml.etree.ElementTree as ET
from io import StringIO
import base64
from waveform_utils import apply_filter, normalize


def read_chunk(input, chunk_offset):
    content = input[chunk_offset:]
    if len(content) < 8:
        return None, None
    header = content[:8]  # treat as little endian
    compressed_data_size = header[:4]
    compressed_data_size = int.from_bytes(compressed_data_size, 'little', signed=True)
    unknown_usage = header[4:6]
    delta_code = header[6:8]
    delta_code = struct.unpack('h' * (len(delta_code) // 2), delta_code)

    content = content[8:]
    compressed_data = content[:compressed_data_size]
    assert len(compressed_data) == compressed_data_size

    compressed_data = [int(str(x)) for x in compressed_data]
    decompressed_data = []
    lzw = Lzw(compressed_data)
    while True:
        next_val = lzw.read()
        if next_val is None:
            break
        decompressed_data.append(next_val)

    if len(decompressed_data) % 2 == 1:
        decompressed_data.append(0)

    unpacked_data = unpack(decompressed_data)
    decoded = decode_deltas(unpacked_data, delta_code[0])

    return chunk_offset + 8 + compressed_data_size, decoded


def reconstitute_leads(leads):
    lead_I = leads[0]
    lead_II = leads[1]
    lead_III = leads[2]
    lead_AVR = leads[3]
    lead_AVL = leads[4]
    lead_AVF = leads[5]

    # Lead III
    for i in range(len(lead_III)):
        lead_III[i] = lead_II[i] - lead_I[i] - lead_III[i]

    # Lead aVR
    for i in range(len(lead_AVR)):
        lead_AVR[i] = -1 * lead_AVR[i] - ((lead_I[i] + lead_II[i]) / 2)

    # Lead aVL
    for i in range(len(lead_AVL)):
        lead_AVL[i] = ((lead_I[i] - lead_III[i]) / 2) - lead_AVL[i]

    # Lead aVF
    for i in range(len(lead_AVF)):
        lead_AVF[i] = ((lead_II[i] + lead_III[i]) / 2) - lead_AVF[i]


def create_from_lead_set(lead_data):
    leads = []
    for lead in lead_data:
        leads.append(lead)
        if len(leads) >= 12:
            break
    reconstitute_leads(leads)
    return leads


def unpack(bytes_arr):
    actual = []
    actual_len = int(len(bytes_arr) / 2)
    for i in range(actual_len):
        hi = (bytes_arr[i] << 8) & 0xFFFF
        lo = bytes_arr[actual_len + i] & 0xFF
        actual.append(ctypes.c_int16(hi | lo).value)
    return actual


def decode_deltas(input, initial_value):
    deltas = input.copy()
    x = deltas[0]
    y = deltas[1]
    last_value = initial_value
    i = 2
    while i < len(deltas):
        z = (y + y) - x - last_value
        last_value = deltas[i] - 64
        deltas[i] = z
        x = y
        y = z
        i += 1
    return deltas


def get_global_measurement(globalmeasurements, attr):
    elems = globalmeasurements.findall(attr)
    if len(elems) > 0:
        return globalmeasurements.findall(attr)[0].text
    else:
        return ""


def parse_file_with_encoding(input_file):
    # We read the file into a string first to get around the problem where some files
    # are encoded incorrectly (e.g. XML header indicates UTF-16, but actually is UTF-8)
    try:
        txt = Path(input_file).read_text()
    except Exception as e:
        txt = Path(input_file).read_text(encoding='utf-16')

    it = ET.iterparse(StringIO(txt))

    for _, el in it:
        prefix, has_namespace, postfix = el.tag.partition('}')
        if has_namespace:
            el.tag = postfix
    return it.root


def parse(input_file):
    root = parse_file_with_encoding(input_file)

    # Parse out all elements
    #
    reportinfo = root.findall('reportinfo')[0]
    report_date = reportinfo.attrib["date"]
    report_time = reportinfo.attrib["time"]

    patient = root.findall("patient")[0]
    generalpatientdata = patient.findall("generalpatientdata")[0]
    age_elem = generalpatientdata.findall("age")[0]
    sex = generalpatientdata.findall("sex")[0].text
    dateofbirth = age_elem.findall("dateofbirth")[0].text

    order_info = root.findall("orderinfo")[0]
    mrn = order_info.findall("ordernumber")[0].text

    dataacquisition = root.findall("dataacquisition")[0]
    acquirer = dataacquisition.findall("acquirer")[0]
    csn = acquirer.findall("encounterid")[0].text

    internalmeasurements = root.findall("internalmeasurements")[0]
    crossleadmeasurements = internalmeasurements.findall("crossleadmeasurements")[0]
    if len(crossleadmeasurements.findall("meanqrsdur")) > 0:
        meanqrsdur = crossleadmeasurements.findall("meanqrsdur")[0].text
    if len(crossleadmeasurements.findall("meanprint")) > 0:
        meanprint = crossleadmeasurements.findall("meanprint")[0].text

    output_rows = []
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
        try:
            severity = interpretation.findall('severity')[0].text.replace("-", "").strip()
        except Exception as e:
            severity = ""
        statements = interpretation.findall('statement')
        leftstatements = []
        for statement in statements:
            leftstatement = statement.findall('leftstatement')[0].text
            if leftstatement is not None:
                leftstatements.append(leftstatement)

        output_row = [report_date, report_time, dateofbirth, sex, mrn, csn, meanqrsdur, meanprint,
                      heartrate, rrint, pdur, qonset, tonset, qtint, qtcb, qtcf, QTcFm, QTcH,
                      pfrontaxis, i40frontaxis, qrsfrontaxis, stfrontaxis, tfrontaxis, phorizaxis, i40horizaxis,
                      t40horizaxis, qrshorizaxis, sthorizaxis, severity, ",".join(leftstatements)]
        output_rows.append(output_row)

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

    return output_rows, np.array(processed_leads)
