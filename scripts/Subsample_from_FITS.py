#! /usr/bin/env python

import argparse
from collections import OrderedDict
from astropy.io import fits
from astropy.io import ascii
import numpy as np
import bisect
from math import ceil

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-i', '--input',
        help="Name of the input catalogue",
        action="store", 
        type=str, 
        dest="input", 
        required=True
    )

    parser.add_argument(
        '-o', '--output',
        help="Name of the output catalogue",
        action="store", 
        type=str, 
        dest="output",
        required=True
    )

    parser.add_argument(
        '--ID-list',
        help="List of object IDs to copy to the new file",
        action="store", 
        type=str, 
        dest="ID_list"
    )

    parser.add_argument(
        '--ID-key',
        help="Column name containing object IDs",
        action="store", 
        type=str, 
        default="ID",
        dest="ID_key"
    )

    parser.add_argument(
        '--ID-filename',
        help="File containing list of object IDs to copy to the new file",
        action="store", 
        type=str, 
        dest="ID_file_list"
    )

    parser.add_argument(
        '-n', '--number',
        help="Number of catalogue entries to copy to new file.",
        action="store", 
        type=float,
        dest="n_objects"
    )

    parser.add_argument(
        '--shuffle',
        help="Whether to shuffle the catalogue entries or not.",
        action="store_true", 
        default = False,
        dest="shuffle"
    )

    parser.add_argument(
        '-f', '--force',
        help="Force overwriting of an already existing file.",
        action="store_true", 
        default = False,
        dest="overwrite"
    )

    parser.add_argument(
        '--seed',
        help="Seed of random number random generator",
        action="store", 
        type=int,
        default=12345,
        dest="seed"
    )

    parser.add_argument(
        '--band-list',
        help="List of column names containing photometric bands",
        action="store", 
        type=str, 
        nargs="+",
        dest="band_list"
    )

    parser.add_argument(
        '--error-prefix',
        help="Prefix indicating the columns containing the flux errors",
        action="store", 
        type=str, 
        dest="error_prefix"
    )

    parser.add_argument(
        '--error-suffix',
        help="Suffix indicating the columns containing the flux errors",
        action="store", 
        type=str, 
        dest="error_suffix",
        default="_err"
    )

    parser.add_argument(
        '--SN-threshold',
        help="S/N threshold to select objects",
        action="store", 
        type=np.float32, 
        dest="SN_threshold"
    )

    parser.add_argument(
        '--SN-n-bands',
        help="Minimum number of photometric bands that must satisfy the S/N threshold to select objects",
        action="store", 
        type=np.int, 
        dest="SN_n_bands"
    )

    # Get parsed arguments
    args = parser.parse_args()    

    # Seed for random number generator
    np.random.seed(args.seed)

    # Open the input photometric catalogue
    hdu = fits.open(args.input)[1]
    n_rows = len(hdu.data[args.ID_key])
    mask = np.zeros(n_rows, dtype=bool)
    ID_to_copy = None

    # Check if input and output file coincides
    if args.output == args.input:
        raise IOError('Ouput and input filenames coincide!!')

    if args.ID_list is not None:
        ID_to_copy = [item for item in args.ID_list.split(',')]
    elif args.ID_file_list is not None:
        if args.ID_file_list.endswith(('fits', 'fit', 'FITS', 'FIT')):
            tmp = fits.open(args.ID_file_list)[1].data
        else:
            tmp = ascii.read(args.ID_file_list, Reader=ascii.basic.CommentedHeader)
        ID_to_copy = tmp[args.ID_key]

    # Check if you want to select only objects satisfying a S/N in given bands
    if args.SN_threshold is not None:
        if args.band_list is None:
            parser.error("The option '--SN-threshold' requires the option '--band-list'")

        if args.SN_n_bands is None:
            parser.error("The option '--SN-threshold' requires the option '--SN-n-bands'")

        SN = OrderedDict()
        n_bands = len(args.band_list)
        SN_mask = np.zeros((n_rows,n_bands), dtype=int)

        for i, band in enumerate(args.band_list):
            print "band: ", band
            if args.error_prefix is not None:
                err = args.error_prefix + band
            else:
                err = band + args.error_suffix

            SN[band] = hdu.data[band]/hdu.data[err]
            loc = np.where(hdu.data[err] < 0.)[0]
            SN[band][loc] = -99.
            
            loc = np.where(SN[band] >= args.SN_threshold)[0]
            SN_mask[loc, i] = 1

        SN_selec_mask = np.sum(SN_mask, axis=1)
        loc = np.where(SN_selec_mask >= args.SN_n_bands)[0]
        mask[loc] = True

    # Select some columns from the original file
    #new_columns = (hdu.columns['ID'], hdu.columns['SPECZ'])

    # Create new FITS file from these columns
    #new_hdu = fits.BinTableHDU.from_columns(new_columns)

    # And write it to the disk!
    #new_hdu.writeto('hlsp_uvudf_hst_v2.0_cat_SPECZ_2col.fits')

    #ID_to_copy = np.array([6541, 8002, 8575, 8942, 9467, 25335], dtype=np.int)
    #IDs_high_p = (7643, 6106, 5017, 3939, 2723, 2634,20150, 5602, 7381, 8231,24515, 78)
    #IDs_low_p= (5708, 6714, 22925, 22230, 5642, 33821, 5338, 9177, 24394, 9177, 2611, 511, 76)
    #ID_to_copy = np.array(IDs_low_p+IDs_high_p, dtype=np.int)

    if args.n_objects is not None:
        if args.n_objects < 1:
            n_objects = ceil(args.n_objects*n_rows)
        else:
            n_objects = int(args.n_objects)
        mask[0:n_objects] = True
        if args.shuffle:
            mask = np.random.permutation(mask)

    elif ID_to_copy is not None:
        if isinstance(hdu.data[args.ID_key][0], basestring):
            for ID in ID_to_copy:
                #print "ID----> ", ID
                #indx = np.where(hdu.data['ID'] == ID)[0]
                #print "indx: ", indx
                mask[hdu.data[args.ID_key] == ID] = True
        else:
            for i in range(len(ID_to_copy)):
                i1 = bisect.bisect_left(hdu.data[args.ID_key], ID_to_copy[i])
                # You may have (numeric) IDs in the input list which go beyond
                # the available IDs in the orginal catalogue, in which case 
                # the bisection will give an index equal to the length of the
                # array
                if (i1 >= n_rows):
                    continue
                if hdu.data[args.ID_key][i1] == ID_to_copy[i]:
                    mask[i1] = True

    hdu.data = hdu.data[mask]
    hdu.writeto(args.output, overwrite=args.overwrite)
