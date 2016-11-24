#!/bin/bash

echo `find . -name '*BEAGLE.fits.gz' ! -size 0 | wc -l`

