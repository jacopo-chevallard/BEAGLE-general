#! /usr/bin/env python

import numpy as np
from astropy.io import fits, ascii
import os
import json
from collections import OrderedDict
import argparse

# Name of the JSON dictionary containing the name of the grid parameters 
_GRID_PARAM_KEY = "parameters"

# Name of the JSON dictionary containing the additional quantities (e.g. from
# the *color files) that will be included in the FITS file
_ADDITIONAL_Q_KEY = "additional quantities"

# Name of the JSON dictionary containing the pairs keyword:value that will be
# added to the header of the _HDU_PARAMETERS_NAME extension
_HEADER_KEY = "header"

# Name of the HDU extension containing the value of the template parameters
_HDU_PARAMETERS_NAME = "PARAMETERS GRID"

# Name of the HDU extension containing the template spectra and additional quantities
_HDU_GRID_NAME = "SPECTRUM GRID"

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-i', '--input',
        help="ASCII file containing the list of *ised_ASCII files that will be converted into FITS format",
        action="store", 
        type=str, 
        dest="input_file", 
        required=True
    )

    parser.add_argument(
        '--JSON-file',
        help="JSON file containing the configuration of then templates that will be converted to FITS format",
        action="store", 
        type=str, 
        dest="json_file",
        required=True
    )

    parser.add_argument(
        '--split-files',
        help="Create one FITS file per metallicity",
        action="store_true", 
        dest="split_files"
    )

    # Get parsed arguments
    args = parser.parse_args()    

    # File containing the list of files that will be integrated into a single FITS table
    mixtures = ascii.read(args.input_file, format="commented_header")

    with open(args.json_file) as f:
        json_data = json.load(f, object_pairs_hook=OrderedDict)

    # Parameters defining the grid over which the template spectra are computed
    grid_params = json_data[_GRID_PARAM_KEY]

    additional_quantities = None
    if _ADDITIONAL_Q_KEY in json_data:
        additional_quantities = json_data[_ADDITIONAL_Q_KEY]

    header = None
    if _HEADER_KEY in json_data:
        header = json_data[_HEADER_KEY]

    # Initialize empty dictionaries
    # One dictionary that will contain the actual spectra
    data = OrderedDict()

    # Another dictionary that will contain the parameter values
    grid = OrderedDict()

    # Initialize an empty list for the grid dictionary
    # Each list will contain the actual values of the parameter
    grid["spectrum"] = list()

    # Cycle across all input files
    for m in mixtures:

        file_name = m["file_name"]
        with open(file_name, 'r') as f:

            # Read time steps
            line = f.readline().split()
            n_age = np.int(line[0])
            print "Number of time steps: ", n_age

            time_steps = np.array(line[1:n_age+1], dtype=np.float32)
            print "Time steps: ", time_steps
            if "age" not in grid:
                grid["age"] = time_steps
            else:
                grid["age"] = np.concatenate((grid["age"], time_steps))

            if "metallicity" not in grid:
                grid["metallicity"] =  np.repeat(m["metallicity"], n_age)
            else:
                grid["metallicity"] =  np.concatenate((grid["metallicity"], np.repeat(m["metallicity"], n_age)))
            print "metallicity: ",  grid["metallicity"]

            # Lower and upper mass cutoff of the IMS
            m_low, m_up, n_seg = f.readline().split()
            print "Lower and upper mass cutoff of the IMF: ", m_low, m_up

            # Number of segments in the IMS
            print "Number of segments of the IMF: ", n_seg

            # Skip lines
            n_skip = 4
            for i in range(n_skip):
                line = f.readline()
                print "Skipped line: ", line

            # Read wavelengths
            line = f.readline().split()
            n_wl = np.int(line[0])
            print "Number of wl points: ", n_wl

            wl = np.array(line[1:n_wl+1], dtype=np.float32)

            data["wl"] = wl
            print "Wl points: ", wl

            # Read the fluxes
            for i in range(n_age):
                line = f.readline().split()
                spectrum = np.array(line[1:n_wl+1], dtype=np.float32)
                grid["spectrum"].append(spectrum)


            # Add the "additional quantities"
            if additional_quantities is not None:
                for add in additional_quantities:
                    file_ = os.path.splitext(file_name)[0]+ "." + add["suffix"]
                    n_lines = sum(1 for line in open(file_))
                    header_start = n_lines - n_age
                    data_ = ascii.read(file_, format="commented_header", header_start=header_start)
                    has_zero_age = True
                    if len(data_.field(0)) < n_age:
                        has_zero_age = False
                    for q in add["quantities"]:
                        if has_zero_age:
                            d_ = data_[q]
                        else:
                            d_ = np.concatenate(([data_[q][0]], data_[q]))

                        if q not in grid:
                            grid[q] = d_
                        else:
                            grid[q] = np.concatenate((grid[q], d_))


    # Create the columns which will hold the parameter grid
    cols = list()

    # Column containing the wl array
    _n = len(data["wl"]) ; dim_str = '(' + str(_n) + ')'
    col = fits.Column(name="wavelengths", format=str(_n) + 'E', dim=dim_str, unit='Ang') ; cols.append(col)

    # Column containing the FWHM array
    col = fits.Column(name="FWHM", format=str(_n) + 'E', dim=dim_str, unit='Ang') ; cols.append(col)

    # The other columns containing the parameter grid
    n_metal = 1
    for par in grid_params:
      _par_values = np.unique(np.array(grid[par]))
      if args.split_files and par == 'metallicity':
          n_metal = len(_par_values)
          col = fits.Column(name=par, format='E')
          cols.append(col)
      else:
          _n = len(_par_values) ; dim_str = '(' + str(_n) + ')'
          col = fits.Column(name=par, format=str(_n) + 'E', dim=dim_str)
          cols.append(col)

    initial_cols = fits.ColDefs(cols)

    for i in range(n_metal):

        # We create a FITS Primary array, which will be the first extention of the output FITS file (it is mandatory)
        hdulist = fits.HDUList([fits.PrimaryHDU()])
        new_hdu = fits.BinTableHDU.from_columns(initial_cols, nrows=1)

        # Fill the columns containing the parameter grid values
        new_hdu.data["wavelengths"] = data["wl"]
        for par in grid_params:
            
          if args.split_files and par == 'metallicity':
              _par_values = np.unique(np.array(grid[par]))
              new_hdu.data[par] = _par_values[i]
              metallicity =  _par_values[i]
          else:
              _par_values = np.unique(np.array(grid[par]))
              new_hdu.data[par] = _par_values

        # Add header keywords
        if header is not None:
            for key, value in header.iteritems():
                new_hdu.header[key] = value

        # Name of the FITS extension
        new_hdu.name = _HDU_PARAMETERS_NAME

        # Append the HDU to the HDU list
        hdulist.append(new_hdu)

        # Create the columns which will hold the spectrum at each point in the grid
        cols = list()
        for par in grid_params:
          col = fits.Column(name=par, format='E') ; cols.append(col)
          
        _n = len(grid["spectrum"][0])
        dim_str = '(' + str(_n) + ')'
        col = fits.Column(name="spectrum", format=str(_n) + 'E', dim=dim_str) ; cols.append(col)

        # Create other columns for the return fraction and so on
        if additional_quantities is not None:
            for add in additional_quantities:
                for q in add["quantities"]:
                    col = fits.Column(name=q, format='E') ; cols.append(col)

        _cols = fits.ColDefs(cols)
        nrows = len(grid["age"])/n_metal

        new_hdu = fits.BinTableHDU.from_columns(_cols, nrows=nrows)
        new_hdu.name = _HDU_GRID_NAME

        # Fill the hdu!
        j = 0
        for i in range(len(grid["age"])):
            if args.split_files:
                if grid["metallicity"][i] != metallicity:
                    continue
            for par in grid_params:
                new_hdu.data[par][j] = grid[par][i]
            new_hdu.data["spectrum"][j] = grid["spectrum"][i]
            if additional_quantities is not None:
                for add in additional_quantities:
                    for q in add["quantities"]:
                        new_hdu.data[q][j] = grid[q][i]
            j += 1

        # Append the HDU to the HDU list
        hdulist.append(new_hdu)

        # Finally, write the file to the disk!
        if args.split_files:
            file_name = os.path.splitext(args.input_file)[0] + "_Z_" + str(metallicity) + ".fits"
        else:
            file_name = os.path.splitext(args.input_file)[0]+ ".fits"

        hdulist.writeto(file_name, overwrite=True)

