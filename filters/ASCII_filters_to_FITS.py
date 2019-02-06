#!/usr/bin/env python

import argparse
import os
import numpy as np
from astropy.table import Table
from collections import OrderedDict
from astropy.io import fits

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-i', '--input',
        help="Name of the input ASCII file containing the filters transmission curves.",
        action="store", 
        type=str, 
        dest="input", 
        required=True
    )

    parser.add_argument(
        '-o', '--output',
        help="Name of the output FITS file.",
        action="store", 
        type=str, 
        dest="output" 
    )

    # Get parsed arguments
    args = parser.parse_args()    

    if args.output is None:
        args.output = os.path.splitext(args.input)[0] + '.fits'

    f_in = open(args.input, 'r')

    data = OrderedDict()

    n_filters = 0

    for line in f_in:

        if line.startswith("#"):
            n_filters += 1
            line = line.strip()

            if data:
                data[band].update({"transmission":np.array(transmission)})

            transmission = list()

            line  = line.replace("(", "")
            line  = line.replace(")", "")
            line_split = line.split(' ')
            if len(line_split) > 2:
                band = line_split[1] + '_' + line_split[2]
            else:
                band = line_split[1]
            url = ""
            for split in line.split(' '):
                if split.startswith("http") or  split.startswith("www"):
                    url = split

            data[band] = {"url":url}

            continue

        wl_, t_wl_ = line.split()

        transmission.append((wl_, t_wl_))

    print "Total number of filters: ", n_filters 

    data[band].update({"transmission":np.array(transmission)})

    # FITS column containing the metallicities
    colInfo = list()

    name = fits.Column(name='name', format='40A')
    colInfo.append(name)

    col = fits.Column(name='n_wl', format='I')
    colInfo.append(col)

    col = fits.Column(name='url', format='100A')
    colInfo.append(col)

    col = fits.Column(name='description', format='200A')
    colInfo.append(col)

    col = fits.Column(name='airmass', format='E')
    colInfo.append(col)

    # List containing different FITS columns
    colList = list()

    for key, value in data.iteritems():
        n_wl = len(value["transmission"][:,0])
        value["n_wl"] = n_wl
        dim_str = '(' + str(n_wl) + ',' + str(2) + ')'
        L = fits.Column(name=key, format=str(n_wl*2)+'E', dim=dim_str)
        colList.append(L)

    # We create a "ColDefs" instance that we will then use to create the FITS binary table
    cols = fits.ColDefs(colList)

    # We create a FITS Primary array, whcih will be the first extention of the output FITS file (it is mandatory)
    prihdu = fits.PrimaryHDU()

    # List containing the different FITS HDU, i.e. FITS extensions
    hdulist = fits.HDUList([prihdu])

    tbhdu = fits.BinTableHDU.from_columns(cols, nrows=1)
    tbhdu.name = "TRANSMISSION"

    for key, value in data.iteritems():
        tbhdu.data[key][0] = data[key]["transmission"].T

    # Append the HDU to the HDU list
    hdulist.append(tbhdu)

    # Now the extension containing ancillary information
    cols = fits.ColDefs(colInfo)
    tbhdu = fits.BinTableHDU.from_columns(cols, nrows=len(data))
    tbhdu.name = "META DATA"

    i=0
    for key, value in data.iteritems():
        tbhdu.data["name"][i] = key
        tbhdu.data["n_wl"][i] = value["n_wl"]
        tbhdu.data["url"][i] = value["url"]
        i += 1

    hdulist.append(tbhdu)

    # Finally, write the file to the disk!
    hdulist.writeto(args.output, overwrite=True)
