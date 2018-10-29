#! /usr/bin/env python

from astropy.io import fits
import os, glob, sys
import matplotlib.pyplot as plt
import numpy as np
import argparse
from autoscale import autoscale_y
import json 

c_light = 2.99792e+18 # Ang/s

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--file',
        help="File containing BEAGLE results",
        type=str, 
        dest="file", 
        required=True
    )

    parser.add_argument(
        '--row',
        help="Row in the FULL SED extension to be plotted",
        dest="row", 
        type=int,
        nargs="+",
        default=0
    )

    parser.add_argument(
        '--range',
        help="Wavelength range to be plotted",
        dest="xrange", 
        type=np.float32,
        nargs=2,
        default=None
    )

    parser.add_argument(
        '--wl-units',
        help="Wavelength units.",
        action="store",
        type=str,
        dest="wl_units",
        choices=['ang', 'nm', 'micron'],
        default='ang'
        )

    parser.add_argument(
        '--redshift',
        dest="redshift", 
        help="Redshift",
        type=np.float32,
        default=None
        )

    parser.add_argument(
        '--fnu',
        dest="fnu", 
        help="Plot in units of Fnu instead of Flambda",
        action="store_true")

    parser.add_argument(
        '--hdu-name',
        dest="hdu_name", 
        help="Name of the HDU containing the SED to be plotted (it must be a 2D image)",
        type=str,
        default="full sed"
        )
        
    parser.add_argument(
        '--json-legend',
        help="Create a legend from the values in the FITS HDU and FITS column indicated by a JSON string."\
                " Example: '{\"extName\":\"GALAXY PROPERTIES\", \"colName\":\"max_stellar_age\", \"label\":\"age/yr\"}'.",
        action="store", 
        type=str,
        dest="json_legend" 
        )

    parser.add_argument(
        '--normalize',
        help="Renormalize the SED to median flux value of the SED.",
        action="store_true", 
        dest="normalize" 
        )

    parser.add_argument(
        '--log-flux',
        help="Plot logarithmic axis for flux.",
        action="store_true", 
        dest="plot_log_flux" 
        )

    parser.add_argument(
        '--log-wavelength',
        help="Plot logarithmic axis for wavelength.",
        action="store_true", 
        dest="plot_log_wl" 
        )


    args = parser.parse_args()    

    wl_factor = 1.
    if args.wl_units == 'micron':
        wl_factor = 1.E+04
    elif args.wl_units == 'nm':
        wl_factor = 1.E+01

    hdulist = fits.open(args.file)

    # Get the wavelength array
    hdu_name = args.hdu_name + " wl"
    wl = hdulist[hdu_name].data['wl'][0,:]

    # Get the SED
    hdu_name = args.hdu_name
    SEDs = hdulist[hdu_name].data
    if len(SEDs.shape) == 2 :
        sed = SEDs[args.row,:]
    else:
        sed = SEDs

    # Extract the values used in the legend
    if args.json_legend is not None:
        json_leg = obj = json.loads(args.json_legend)
        try:
            extName = json_leg["extName"]
        except:
            raise ValueError('`extName` must be present in the JSON string (see example).')

        try:
            colName = json_leg["colName"]
        except:
            raise ValueError('`colName` must be present in the JSON string (see example).')

        try:
            legend_label = json_leg["label"]
        except:
            raise ValueError('`label` must be present in the JSON string (see example).')

        legend_values = hdulist[extName].data[colName][args.row]

        if "transformation" in json_leg:
            for i, x in enumerate(legend_values):
                x = legend_values[i]
                legend_values[i] = eval(json_leg['transformation'])

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    if args.xrange is not None:
        ax.set_xlim(args.xrange)
        loc = np.where((wl >= args.xrange[0]) & (wl <= args.xrange[1]))[0]
        sed = sed[:, loc]
        wl = wl[loc]

    # Redshift the SED and wl
    if args.redshift is not None:
        sed /= (1.+args.redshift)
        wl *= (1.+args.redshift)

    # Convert F_lambda [erg s^-1 cm^-2 A^-1] ----> F_nu [erg s^-1 cm^-2 Hz^-1]
    if args.fnu:
        sed = wl**2/c_light*sed


    ax.set_xlabel('$\lambda / \mu\\textnormal{m}$')
    if args.fnu:
        ax.set_ylabel('$f_\\nu / \\textnormal{erg} \, \\textnormal{s}^{-1} \, \\textnormal{cm}^{-2} \, \\textnormal{Hz}^{-1} $')
    else:
        ax.set_ylabel('$f_\lambda / \\textnormal{erg} \, \\textnormal{s}^{-1} \, \\textnormal{cm}^{-2} \, \\textnormal{\AA}^{-1} $')

    for i in range(len(args.row)):
        _sed = sed[i,:]
        if args.normalize:
            wl_center = 0.5*(wl[0]+wl[-1]) ; dwl = wl[-1]-wl[0]
            loc = np.where((wl >= (wl_center-dwl*0.1)) & (wl <= (wl_center+dwl*0.1)))[0]
            norm = np.mean(_sed[loc])
            _sed /= norm

        if args.json_legend is not None:
            label = legend_label + " = {:.2e}".format(legend_values[i])
            ax.plot(wl/wl_factor,
                _sed,
               lw=1.0,
               label=label
                )
        else:
            ax.plot(wl/wl_factor,
               _sed,
               lw=1.0
                )
    if args.json_legend is not None:
        ax.legend(fontsize=ax.xaxis.get_label().get_fontsize()*0.7)

    if args.plot_log_wl: 
        ax.set_xscale('log')

    if args.plot_log_flux: 
        ax.set_yscale('symlog')

    autoscale_y(ax)

    plt.show()
    hdulist.close()
