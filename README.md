# Bus Transit Headway Bounds
This repository contains code to reproduce the results in the submission "Computing Headway Bounds under Worst-Case Bunching in Fixed-Line Transit Systems."

## Installing the Requirements
You can either run the notebooks in this repository directly, or use Docker.

### Docker (Recommended)
If you haven't already done so, install [Docker](https://docs.docker.com/engine/install/).

First, build the image using the Dockerfile provided:
```bash
docker build --tag headway-analysis .
```

Next, launch a container and leave a port open for the Jupyter server:
```bash
docker run --rm -p 8888:8888 headway-analysis
```

After the container starts, Jupyter server should publish a URL in the terminal logs.
Copy that into your browser's address bar.

### Native Python
First, clone this repository, and set it as your working directory:
```bash
git clone git@github.com:m-yuhas/bus-transit-headway-bounds.git
cd bus-transit-headway-bounds
```

(Optional) Create a new virtual environment using your favorite virtual environment mangager and install the requirements.
Example for venv:
```bash
python3 -m venv headway-analysis
source headway-analysis/bin/activate
pip install -r requirements.txt
kaleido_get_chrome # Required for Plotly to export images
```

Launch a Jupyter Server:
```bash
jupyter notebook
```

## Generating the Figures

## Organization