## Philips ECG Parser

Parses a Philips XML file by writing the output to a CSV file and saving the ECG waveform as a PNG.

Based on the [Sierra ECG Tools](https://github.com/sixlettervariables/sierra-ecg-tools) by Christopher Watford.

### Installation

Note that both a `requirements.txt` and conda `environment.yml` file to allow dependencies to be installed on a M1-based Mac.

```
conda create -n ecg python=3.8
conda activate ecg
conda env update --file environment.yml
pip install -r requirements.txt
```

### Usage

```
python3 parse_xml.py <ECG XML file> <output CSV> <output 12-lead ECG waveform>
```
