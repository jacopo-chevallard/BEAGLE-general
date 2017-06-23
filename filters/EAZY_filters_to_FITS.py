#!/usr/bin/env python

import argparse
import numpy as np
from astropy.table import Table
from collections import OrderedDict
from astropy.io import fits
import os


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-i', '--input',
        help="Name of the input ASCII file containing the filters transmission curves (EAZY format).",
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
        dest="output",
        required=True
    )

    # Get parsed arguments
    args = parser.parse_args()    

    f_in = open(args.input, 'r')

    data = OrderedDict()
    name = ''

    for i, line in enumerate(f_in):

        is_header = False
        spl = line.split()
        for s in spl:
            try:
                float(s)
            except:
                is_header = True

        if is_header:
            if name in data:
                data[name].update({"transmission":np.array(transmission, dtype=np.float32)})

            n_wl = int(spl[0])
            name = os.path.basename(spl[1]).split('.')[0]

            description = ''
            for s in spl[1:]:
                description = description + ' ' + s

            data[name] = {"n_wl":n_wl}
            data[name].update({"description":description})

            transmission = list()

        else:
            transmission.append((spl[1], spl[2]))

    data[name].update({"transmission":np.array(transmission, dtype=np.float32)})

    # FITS column containing the metallicities
    colInfo = list()

    name = fits.Column(name='name', format='40A')
    colInfo.append(name)

    col = fits.Column(name='n_wl', format='I')
    colInfo.append(col)

    #col = fits.Column(name='url', format='100A')
    #colInfo.append(col)

    col = fits.Column(name='description', format='200A')
    colInfo.append(col)

    #col = fits.Column(name='airmass', format='E')
    #colInfo.append(col)

    # List containing different FITS columns
    colList = list()

    for key, value in data.iteritems():
        n_wl = value["n_wl"]
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
        tbhdu.data[key][0] = value["transmission"].T

    # Append the HDU to the HDU list
    hdulist.append(tbhdu)

    # Now the extension containing ancillary information
    cols = fits.ColDefs(colInfo)
    tbhdu = fits.BinTableHDU.from_columns(cols, nrows=len(data))
    tbhdu.name = "META DATA"

    i=0
    for key, value in data.iteritems():
        tbhdu.data["name"][i] = key
        tbhdu.data["n_wl"][i] = data[key]["n_wl"]
        tbhdu.data["description"][i] = data[key]["description"]
        i += 1

    hdulist.append(tbhdu)

    # Finally, write the file to the disk!
    hdulist.writeto(args.output, clobber=True)
