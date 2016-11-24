#!/bin/bash

# ****************************************
# see this beautiful tutorial on getopt: http://www.bahmanm.com/blogs/command-line-options-how-to-parse-in-bash-using-getopt
# and for long options see here http://stackoverflow.com/questions/7069682/how-to-get-arguments-with-flags-in-bash-script
# ****************************************

display_usage() { 
	echo -e "\nDescription:"\
    "\nrsync to the local folder the files containing the results of a Beagle run."\
    "\nOptions:"\
    "\n--host|-h : full name of the remote machine and folder containing the Beegle results"\
    "\n--number|-n : number of (randomly selected) objects to sync. This option requires "\
      "\nthe presence of *MNstats.txt files in the local folder, since they are used to extract the IDs"\
    "\n--ID : ID of the object whose Beagle results files must be synced"\
    "\n--ID-list : file name containing a list of object whose Beagle results file must be synced"\
	#echo -e "\nUsage:\n\n$0 --host [rsync destination] \n\nExample: $0 --host user@server:/foo/bar\n\n" 
	} 

# if less than one argument supplied, display usage and exit 
if [  $# -le 0 ]; then 
	display_usage
	exit 1
fi 

# default values for input arguments

# Name of the remote host, including the BEAGLE results directory, form which
# the files will be rsynced. Example user@host:foo/bar/Beagle
hostname=""

number=10
seed=1234
ID=""
ID_list=""

# now read and parse the input arguments, some have options, others don't
for arg in "$@"; do

  case "$1" in

    "--ID")  

      shift
      ID=$1
      shift

    "--ID-list")  

      shift
      ID_list=$1
      shift

    "-n"|"--number")  
    
      shift
      number=$1
      echo "Number of (randomly selected) objects that will be copied: " ${number}
      shift
      ;;

    "-h"|"--host")  

      shift
      hostname=$1
      echo "Hostname: " ${hostname}
      shift
      ;;

  esac

done


# Check for presence of mandatory arguments
if [ -z "$hostname" ]; then
  echo "Mandatory argument --host [hostname] not present!"
  exit 1
fi


# This temporary file contains the list of file to be rsynced and it will be
# removed at the end of the script
tempFile="temp_rsync.dat"

# If this temporary file already exists, delete it
if [ -f "$tempFile" ] ; then
  rm $tempFile
fi

suffix="_BEAGLE"
#plots="pybangs/plot/"

# List all files *MNstats*
list="$(find . -name '*MNstats.dat' ! -size 0)"

# Convert the space-separated list into an array
array=($list)

# Just consider the first $number elements, after having shuffled the array
for index in `gshuf --input-range=0-$(( ${#array[*]} - 1 )) | head -${number}`; do

  file=${array[$index]}
  i=$(awk -v a="$file" -v b="$suffix" 'BEGIN{print index(a,b)}')

  file=${file:0:$i-1}

  # Results files
  echo "+ ${file:2}${suffix}.fits.gz" >> ${tempFile}
  echo "+ ${file:2}${suffix}_MNpost_separate.dat" >> ${tempFile}

  # Plots
  #echo "+ ${plots}${file:2}${suffix}*.pdf" >> ${tempFile}

done  

echo "- *" >> ${tempFile}

# Transfer the files to the new location with rsync
rsync -avz --include-from=${tempFile} ${hostname} ./

# Remove the temporary file
#rm ${tempFile}

