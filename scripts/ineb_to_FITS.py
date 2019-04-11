#! /usr/bin/env python

import numpy as np
from astropy.io import fits, ascii
import os
import json
import glob
from collections import OrderedDict
import argparse
import struct as struct

# Name of the JSON dictionary containing the name of the grid parameters 
_GRID_PARAM_KEY = "parameters"

# Name of the JSON dictionary containing the additional quantities (e.g. from
# the *color files) that will be included in the FITS file
_ADDITIONAL_Q_KEY = "additional quantities"

# Name of the JSON dictionary containing the pairs keyword:value that will be
# added to the header of the _HDU_PARAMETERS_NAME extension
_HEADER_KEY = "header"

_TEMPLATES_LIST_KEY = "templates_list"

_LINES_LIST_KEY = "emission_lines_list"

# Name of the HDU extension containing the value of the template parameters
_HDU_PARAMETERS_NAME = "PARAMETERS"

# Name of the HDU extension containing the template continuum spectra and additional quantities
_HDU_CONTINUUM_NAME = "CONTINUUM"

# Name of the HDU extension containing the template emission lines and additional quantities
_HDU_LINES_NAME = "LINES"

_SPECTRUM_KEY = "spectrum"
_LINE_LUMIN_KEY = "line_luminosities"
_LINE_EWS_KEY = "line_EWs"

_LINE_LUMIN_PREFIX = "Lum_"
_LINE_WL_PREFIX = "Wl_"

_GRID_DEFAULT_KEYS = [_SPECTRUM_KEY, _LINE_LUMIN_KEY, _LINE_EWS_KEY]

def add_quantity_to_grid(label, quantity, grid, repeat=1):
    if label not in grid:
        grid[label] = np.repeat(quantity, repeat)
    else:
        grid[label] = np.concatenate((grid[label], np.repeat(quantity, repeat)))

def extract_metallicity(file_name, split='_'):

    spl = os.path.basename(file_name).split(split)
    for s in spl:
        if s.startswith('z'):
            _s = s[1:1] + '.' + s[2:]
            try:
                Z = float(_s)
            except:
                Z = -99.99
            break

    return Z, s

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--JSON-file',
        help="JSON file containing the configuration of then templates that will be converted to FITS format",
        action="store", 
        type=str, 
        dest="json_file",
        required=True
    )

    parser.add_argument(
        '--folder',
        help="Folder containing the input *ineb files",
        action="store", 
        type=str, 
        dest="ineb_folder"
    )


    parser.add_argument(
        '--split-files',
        help="Create one FITS file per metallicity",
        action="store_true", 
        dest="split_files"
    )

    # Get parsed arguments
    args = parser.parse_args()    

    with open(args.json_file) as f:
        json_data = json.load(f, object_pairs_hook=OrderedDict)

    # File containing the list of files that will be integrated into a single FITS table
    input_file_list = json_data[_TEMPLATES_LIST_KEY]
    templates = ascii.read(input_file_list, format="commented_header")

    # Parameters defining the grid over which the template spectra are computed
    grid_params = json_data[_GRID_PARAM_KEY]

    additional_quantities = None
    if _ADDITIONAL_Q_KEY in json_data:
        additional_quantities = json_data[_ADDITIONAL_Q_KEY]

    header = None
    if _HEADER_KEY in json_data:
        header = json_data[_HEADER_KEY]

    emission_line_file = os.path.expandvars(json_data[_LINES_LIST_KEY])
    _wl = list() ; _use = list() ; _names = list()
    with open(emission_line_file, 'r') as f:
        for line in f:
            _line = line.split()
            _wl.append(np.float32(_line[0].split(':')[1]))
            _u = _line[1].split(':')[1].upper()  
            if _u == "T":
                _use.append(True)
            elif _u == "F":
                _use.append(False)
            else:
                raise ValueError("Boolean string %s not recognized!" % _u)
            _names.append(str(_line[3].split(':')[1]))

    emission_lines = OrderedDict()
    emission_lines["wl"], emission_lines["use"], emission_lines["names"] = np.array(_wl), np.array(_use), np.array(_names)

    # Initialize empty dictionaries
    # One dictionary that will contain the actual spectra
    data = OrderedDict()

    # Another dictionary that will contain the parameter values
    grid = OrderedDict()

    # Initialize an empty list for the grid dictionary
    # Each list will contain the actual values of the parameter
    grid[_SPECTRUM_KEY] = list()
    grid[_LINE_LUMIN_KEY] = list()
    grid[_LINE_EWS_KEY] = list()

    is_first = True
    n_age_lines = 0

    # Cycle across all input files
    for template in templates:

        file_name = os.path.expandvars(template["file_name"])
        if args.ineb_folder is not None:
            file_name = os.path.join(args.ineb_folder, file_name)

        with open(file_name, 'r') as f:

            # read all the content of one .ineb binary file
            fileContent = f.read()

            # Read time steps
            ini=4 # start from 4 because you skip the first line
            fin=ini+4
            nsteps=struct.unpack("i", fileContent[ini:fin]) # number of timesteps
            n_age = np.int(nsteps[0])
            print "Number of time steps: ", n_age

            ini=fin
            fin=ini+4*nsteps[0]
            time_steps = struct.unpack(("f"*nsteps[0]),fileContent[ini:fin])

            if "age" not in grid:
                grid["age"] = time_steps
            else:
                grid["age"] = np.concatenate((grid["age"], time_steps))

            for par in grid_params:
                if par == "age":
                    continue

                if par not in grid:
                    grid[par] =  np.repeat(template[par], n_age)
                else:
                    grid[par] =  np.concatenate((grid[par], np.repeat(template[par], n_age)))

                print par,  template[par]


            # Lower and upper mass cutoff of the IMS
            #m_low, m_up, n_seg = f.readline().split()
            #print "Lower and upper mass cutoff of the IMF: ", m_low, m_up

            # Number of segments in the IMS
            #print "Number of segments of the IMF: ", n_seg

            # Skip lines
            #n_skip = 4
            #for i in range(n_skip):
            #    line = f.readline()
            #    print "Skipped line: ", line

            # Read wavelengths
            ini=fin+8 # skip 2 lines
            fin=ini+4
            incm = struct.unpack("i",fileContent[ini:fin])

            ini=fin
            fin=ini+4*incm[0]
            wl =struct.unpack("f"*incm[0],fileContent[ini:fin])
            wl = np.array(wl, dtype=np.float32)
            n_wl = len(wl)  # this is the same thing of incm
            print "Number of wl points: ", n_wl

            data["wl"] = wl
            print "Wl points: ", wl
    
            # Read the fluxes
            ini=fin
            fin=ini+4
            tag = struct.unpack("i",fileContent[ini:fin])

            ini=fin
            fin=ini+4
            tag = struct.unpack("i",fileContent[ini:fin])

            ini=fin
            fin=ini+4
            mHIIR = struct.unpack("f",fileContent[ini:fin])
            add_quantity_to_grid('mHIIR', mHIIR, grid, repeat=n_age)

            ini=fin
            fin=ini+4
            epsfil = struct.unpack("f",fileContent[ini:fin])
            add_quantity_to_grid('epsfil', epsfil, grid, repeat=n_age)

            ini=fin
            fin=ini+4*2 # skip 2 lines [in the case of kstep=1]
            ini=fin
            fin=ini+4
            rad0= struct.unpack("f",fileContent[ini:fin])
            add_quantity_to_grid('rad0', rad0, grid, repeat=n_age)

            ini=fin
            fin=ini+4
            fracmet = struct.unpack("f",fileContent[ini:fin])
            add_quantity_to_grid('fracmet', fracmet, grid, repeat=n_age)

            ini=fin
            fin=ini+4
            fracdust = struct.unpack("f",fileContent[ini:fin])
            add_quantity_to_grid('fracdust', fracdust, grid, repeat=n_age)

            print ""
            print "mHIIR, epsfil, fracmet, fracdust: ", mHIIR, epsfil, fracmet, fracdust

            for i in range(n_age):
                if i == 0:
                    ini=fin+2*4 # skip 2 lines 
                    fin=ini+4

                ini=fin
                fin=ini+4
                tag = struct.unpack("i",fileContent[ini:fin])

                ini=fin
                fin=ini+4
                colden = struct.unpack("f",fileContent[ini:fin])
                add_quantity_to_grid('colden', colden, grid)

                ini=fin
                fin=ini+4
                temp_elec = struct.unpack("f",fileContent[ini:fin])
                add_quantity_to_grid('temp_elec', temp_elec, grid)

                ini=fin
                fin=ini+4
                temp_eden_elec = struct.unpack("f",fileContent[ini:fin])
                add_quantity_to_grid('temp_eden_elec', temp_eden_elec, grid)

                ini=fin
                fin=ini+4
                qlyc = struct.unpack("f",fileContent[ini:fin])
                add_quantity_to_grid('qlyc', qlyc, grid)


                ini=fin+8*16 # skip all the bytes of the ionic fractions
                ini=ini+2*4  # skip 2 lines
                fin=ini+4
                skipt = struct.unpack("i",fileContent[ini:fin])[0]

                #print skipt[0]
                ini=fin+4*2
                fin=ini+4
                prova = struct.unpack("i",fileContent[ini:fin])

                ini=fin
                fin=ini+4*incm[0]
                # read the continuum
                spectrum = struct.unpack("f"*incm[0],fileContent[ini:fin]) #continuum flux
                spectrum = np.array(spectrum, dtype=np.float32)
                grid[_SPECTRUM_KEY].append(spectrum)
            
                #print "spectrum: ", spectrum
                #print "skipt: ", skipt

                ini=fin # skip line
                fin=ini+4

                if skipt == 0:
                    if is_first:
                        n_age_lines += 1

                    ini=fin # skip line
                    fin=ini+4
                    ini=fin 
                    fin=ini+4

                    n_lines = struct.unpack("i",fileContent[ini:fin])[0] # read number of emission lines
                    line_luminosities = np.zeros(n_lines)
                    line_EWs = np.zeros(n_lines)

                    for l in range(n_lines):
                        # read line luminosity
                        ini=fin
                        fin=ini+4
                        lum = struct.unpack("f",fileContent[ini:fin])[0]
                        line_luminosities[l] = lum

                        # read line EW
                        ini=fin
                        fin=ini+4
                        ew = struct.unpack("f",fileContent[ini:fin])[0]
                        line_EWs[l] = ew

                    grid[_LINE_LUMIN_KEY].append(line_luminosities)
                    grid[_LINE_EWS_KEY].append(line_EWs)

                    ini=fin
                    fin=ini+4
                    tag = struct.unpack("i",fileContent[ini:fin])
                else:
                    grid[_LINE_LUMIN_KEY].append(None)
                    grid[_LINE_EWS_KEY].append(None)

            # Add the "additional quantities"
            if additional_quantities is not None:
                for add in additional_quantities:
                    file_ = os.path.expandvars(os.path.splitext(file_name)[0]+ "." + add["suffix"])
                    if not os.path.isfile(file_):
                        Z, Z_str = extract_metallicity(file_)
                        _dir = os.path.dirname(file_name)
                        if "folder" in add:
                            _dir = os.path.expandvars(add["folder"])
                        _regex = ''
                        if "prefix" in add:
                            _regex = _regex + add["prefix"] + '*'
                        _regex = _regex + Z_str + '*' + add["suffix"]
                        _regex = os.path.join(_dir, _regex)
                        file_ = glob.glob(_regex)[0]

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

        is_first = False

    # ------------------------------------------------------------------------------------
    # We create a FITS Primary array, which will be the first extention of the output FITS file (it is mandatory)
    # ------------------------------------------------------------------------------------

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
          n_metal = len(_par_values) ; dim_str = '(' + str(1) + ')'
          col = fits.Column(name=par, format=str(1) + 'E', dim=dim_str)
          cols.append(col)
      else:
          _n = len(_par_values) ; dim_str = '(' + str(_n) + ')'
          col = fits.Column(name=par, format=str(_n) + 'E', dim=dim_str)
          cols.append(col)

    for l, name in enumerate(emission_lines["names"]):
        if emission_lines["use"][l]:
            _name = _LINE_WL_PREFIX + name
            col = fits.Column(name=_name, format='E', unit='Ang') ; cols.append(col)

    initial_cols = fits.ColDefs(cols)

    for n in range(n_metal):

        hdulist = fits.HDUList([fits.PrimaryHDU()])
        new_hdu = fits.BinTableHDU.from_columns(initial_cols, nrows=1)

        # Fill the columns containing the parameter grid values
        new_hdu.data["wavelengths"] = data["wl"]
        for par in grid_params:
            
          if args.split_files and par == 'metallicity':
              _par_values = np.unique(np.array(grid[par]))
              new_hdu.data[par] = _par_values[n]
              metallicity =  _par_values[n]
          else:
              _par_values = np.unique(np.array(grid[par]))
              new_hdu.data[par] = _par_values

        for l, name in enumerate(emission_lines["names"]):
            if emission_lines["use"][l]:
                _name = _LINE_WL_PREFIX + name
                new_hdu.data[_name] = emission_lines["wl"][l]

        # Add header keywords
        if header is not None:
            for key, value in header.iteritems():
                new_hdu.header[key] = value

        # Name of the FITS extension
        new_hdu.name = _HDU_PARAMETERS_NAME

        # Append the HDU to the HDU list
        hdulist.append(new_hdu)

        # ------------------------------------------------------------------------------------
        # Create the columns which will hold the spectrum at each point in the grid
        # ------------------------------------------------------------------------------------
        cols = list()
        for par in grid_params:
            col = fits.Column(name=par, format='E') ; cols.append(col)
          
        _n = len(grid[_SPECTRUM_KEY][0])
        dim_str = '(' + str(_n) + ')'
        col = fits.Column(name=_SPECTRUM_KEY, format=str(_n) + 'E', dim=dim_str, unit='erg s^-1 Ang^-1') ; cols.append(col)

        # Create other columns for the return fraction and so on
        if additional_quantities is not None:
            for add in additional_quantities:
                for q in add["quantities"]:
                    col = fits.Column(name=q, format='E') ; cols.append(col)

        _cols = fits.ColDefs(cols)
        nrows = len(grid["age"])/n_metal

        new_hdu = fits.BinTableHDU.from_columns(_cols, nrows=nrows)
        new_hdu.name = _HDU_CONTINUUM_NAME

        # Fill the hdu!
        row = 0
        for i in range(len(grid["age"])):
            if args.split_files:
                if grid["metallicity"][i] != metallicity:
                    continue
            #print "row, i:  ", row, i
            for par in grid_params:
                new_hdu.data[par][row] = grid[par][i]
            new_hdu.data[_SPECTRUM_KEY][row] = grid[_SPECTRUM_KEY][i]
            if additional_quantities is not None:
                for add in additional_quantities:
                    for q in add["quantities"]:
                        new_hdu.data[q][row] = grid[q][i]
            row += 1

        # Append the HDU to the HDU list
        hdulist.append(new_hdu)

        # ------------------------------------------------------------------------------------
        # Create the columns which will hold the emission lines at each point in the grid
        # ------------------------------------------------------------------------------------
        cols = list()
        for par in grid_params:
            col = fits.Column(name=par, format='E') ; cols.append(col)

        for l, name in enumerate(emission_lines["names"]):
            if emission_lines["use"][l]:
                _name = _LINE_LUMIN_PREFIX + name
                col = fits.Column(name=_name, format='E', unit='log(L_sun)') ; cols.append(col)
          
        # Create other columns for the additional quantities
        for key, value in grid.iteritems():
            if key not in grid_params and key not in _GRID_DEFAULT_KEYS:
                col = fits.Column(name=key, format='E') ; cols.append(col)

        _cols = fits.ColDefs(cols)
        nrows = n_age_lines/n_metal
        nrows = len(grid[_LINE_LUMIN_KEY])/n_metal
        nrows = int(1.*nrows/n_age*n_age_lines)

        new_hdu = fits.BinTableHDU.from_columns(_cols, nrows=nrows)
        new_hdu.name = _HDU_LINES_NAME

        # Fill the hdu!
        row = 0
        for i in range(len(grid["age"])):
            if args.split_files:
                if grid["metallicity"][i] != metallicity:
                    continue

            if grid[_LINE_LUMIN_KEY][i] is None:
                continue

            for par in grid_params:
                new_hdu.data[par][row] = grid[par][i]
            
            for l, name in enumerate(emission_lines["names"]):
                if emission_lines["use"][l]:
                    _name = _LINE_LUMIN_PREFIX + name
                    new_hdu.data[_name][row] = grid[_LINE_LUMIN_KEY][i][l]

            for key, value in grid.iteritems():
                if key not in grid_params and key not in _GRID_DEFAULT_KEYS:
                    new_hdu.data[key][row] = grid[key][i]
            row += 1

        # Append the HDU to the HDU list
        hdulist.append(new_hdu)


        # Finally, write the file to the disk!
        if args.split_files:
            file_name = os.path.splitext(input_file_list)[0] + "_Z_" + str(metallicity) + ".fits"
        else:
            file_name = os.path.splitext(input_file_list)[0]+ ".fits"

        hdulist.writeto(file_name, overwrite=True)

