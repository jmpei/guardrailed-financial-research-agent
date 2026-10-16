#!/bin/sh
# The demo reads the index manifest, the FinanceBench questions and the filing PDFs; all are gitignored.
set -eu
mkdir -p data/index data/financebench/pdfs
cp tests/fixtures/manifest.json data/index/
base=https://raw.githubusercontent.com/patronus-ai/financebench/main
curl -sSfL -o data/financebench/financebench_open_source.jsonl $base/data/financebench_open_source.jsonl
curl -sSfL -o data/financebench/pdfs/3M_2018_10K.pdf $base/pdfs/3M_2018_10K.pdf
