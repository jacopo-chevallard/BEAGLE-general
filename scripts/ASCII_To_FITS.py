#! /usr/bin/env python

from astropy.io import ascii
from astropy.io import fits
import argparse
import os
import numpy as np

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-i', '--input',
        help="name of the input ASCII catalogue",
        action="store", 
        type=str, 
        dest="input", 
        required=True
    )

    parser.add_argument(
        '-o', '--output',
        help="name of the output FITS catalogue",
        action="store", 
        type=str, 
        dest="output" 
    )

    # Get parsed arguments
    args = parser.parse_args()    

    data = ascii.read(args.input, Reader=ascii.basic.CommentedHeader, guess=False)

    if args.output is None:
        output = os.path.splitext(args.input)[0] + '.fits'
    else:
        output = args.output

    message = "Name of the output FITS catalogue: " + output
    print "\n" + "-"*len(message)
    print message
    print "-"*len(message) + '\n'

    cols = list()

    for name in data.colnames:

        form = data.dtype[name]

        # Convert the default double precision to single precision ("E" and "J" types in a FITS file)
        if form == np.float64:
            form = 'E'
        elif form == np.int64:
            form = 'J'

        if isinstance(data[name][0], basestring):
            if 'S' in str(form):
                form = str(form).split('S')[1] + 'A'
            else:
                form = str(form).split('a')[1] + 'A'

        # If the column name is "mask" but it doesn't contain logical values, then we convert 0 and 1 to True/False
        if 'mask' in name:
            tmp = np.zeros(len(data[name]), dtype=np.bool)
            tmp[data[name] == 1] = True
            data[name] = tmp
            form = 'L'
        
        cols.append(fits.Column(name=name, array=data[name], format=form))

    colsDef = fits.ColDefs(cols)

    hdu = fits.BinTableHDU.from_columns(colsDef)

    # Check if the ASCII file contains a 
    # redshift = value
    # line, in which case add a header keyword to set the object redshift
    redshift = None
    with open(args.input) as f:
        for line in f:
            if line.startswith('#'):
                if 'redshift' in line:
                    try:
                        redshift = np.float32(line.split('=')[1])
                    except:
                        pass
            else:
                break

    if redshift is not None:
        hdu.header['redshift'] = redshift

    hdu.writeto(output, overwrite=True)
