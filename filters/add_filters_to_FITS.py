#!/usr/bin/env python

import argparse
import numpy as np
from astropy.table import Table
from collections import OrderedDict
from astropy.io import fits

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--filter',
        help="Name of the input ASCII file containing the filter(s) to be added",
        action="store", 
        type=str, 
        dest="filter", 
        required=True
    )

    parser.add_argument(
        '--fits',
        help="Name of FITS file containing filter transmission curves to which the new curve will be added.",
        action="store", 
        type=str, 
        dest="fits" 
    )

    # Get parsed arguments
    args = parser.parse_args()    

    f_in = open(args.filter, 'r')

    data = OrderedDict()

    for line in f_in:

        if line.startswith("#"):

            line = line.strip()

            if data:
                data[band].update({"transmission":np.array(transmission)})

            transmission = list()

            line  = line.replace("(", "")
            line  = line.replace(")", "")
            band = line.split(' ')[1]
            url = ""
            for split in line.split(' '):
                if split.startswith("http") or  split.startswith("www"):
                    url = split

            data[band] = {"url":url}

            continue

        wl_, t_wl_ = line.split()

        transmission.append((wl_, t_wl_))

    data[band].update({"transmission":np.array(transmission)})

    # Add new filters to the TRANSMISSION extension
    hdulist = fits.open(args.fits)

    columns = hdulist['TRANSMISSION'].columns
    colList = list()
    for col in columns:
        colList.append(col)

    for key, value in data.iteritems():
        n_wl = len(value["transmission"][:,0])
        value["n_wl"] = n_wl
        dim_str = '(' + str(n_wl) + ',' + str(2) + ')'
        print "key: ", key
        L = fits.Column(name=key, format=str(n_wl*2)+'E', dim=dim_str)
        colList.append(L)

    cols = fits.ColDefs(colList)

    new_hdulist = fits.HDUList([hdulist[0]])

    tbhdu = fits.BinTableHDU.from_columns(cols, nrows=1)
    tbhdu.name = "TRANSMISSION"

    for key, value in data.iteritems():
        tbhdu.data[key][0] = data[key]["transmission"].T

    new_hdulist.append(tbhdu)

    # Add new filters to the META DATA extension
    columns = hdulist['META DATA'].columns

    n_rows = len(hdulist['META DATA'].data.field(0))
    new_n_rows = n_rows + len(data)

    tbhdu = fits.BinTableHDU.from_columns(columns, nrows=new_n_rows)
    tbhdu.name = "META DATA"

    for i in range(n_rows):
        tbhdu.data["name"][i] = hdulist['META DATA'].data["name"][i]
        tbhdu.data["n_wl"][i] = hdulist['META DATA'].data["n_wl"][i]

        if "description" in columns.names:
            tbhdu.data["description"][i] = hdulist['META DATA'].data["description"][i]

        if "url" in columns.names:
            tbhdu.data["url"][i] = hdulist['META DATA'].data["url"][i]

        if "airmass" in columns.names:
            tbhdu.data["airmass"][i] = hdulist['META DATA'].data["airmass"][i]

    i = n_rows
    for key, value in data.iteritems():

        tbhdu.data["name"][i] = key
        tbhdu.data["n_wl"][i] = value["n_wl"]

        if "description" in value and "description" in columns.names:
            tbhdu.data["description"][i] = value["description"]

        if "url" in value and "url" in columns.names:
            tbhdu.data["url"][i] = value["url"]

        if "airmass" in value and "airmass" in columns.names:
            tbhdu.data["airmass"][i] = value["airmass"]

        i += 1


    new_hdulist.append(tbhdu)

    # Finally, write the file to the disk!
    new_hdulist.writeto(args.fits, clobber=True)
