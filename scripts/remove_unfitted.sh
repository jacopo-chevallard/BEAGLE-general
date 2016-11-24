#!/bin/bash

display_usage() { 
	echo -e "\nDescription:\nIt removes files created by BEAGLE when they correspond to objects for which the fitting was not completed.\n"
	echo -e "\nUsage:\n$0 --silent/-s --results/-r [directory containing BEAGLE results]"
	echo -e "\nExample:\n$0 --results /Users/John/BEAGLE \n" 
	} 

# if less than one argument supplied, display usage and exit 
#if [  $# -le 0 ]; then 
#	display_usage
#	exit 1
#fi 

# default values for input arguments
verbose=true
resultsDir="."

# now read and parse the input arguments, some have options, others don't
for arg in "$@"; do

  case "$1" in

    "-h"|"--help")  

      display_usage
      exit 1
      ;;

    "-s"|"--silent")  

      shift
      verbose=false
      ;;

    "-r"|"--results")  

      shift
      resultsDir=$1
      ;;

    *) 

      echo "Option '${1}' not recognized!"
      echo "Type '${0} --help' for information on how to use the script"
      exit 1
      ;;

  esac

done

print_files() { 
	echo -e "\nThe following files will be removed:" 
  arg=("$@")

  for ((i=0;i<=$#;i++)) ; do
    echo "${arg[i]}"
  done
	} 

suffix="_BEAGLE"

list="$(find ${resultsDir} -name '*fits.gz' -size 0)"

for file in $list ; do
  i=$(awk -v a="$file" -v b="${suffix}.fits.gz" 'BEGIN{print index(a,b)}')

  file=${file:0:$i-1}

  rm_files="${file}${suffix}.fits.gz ${file}.lock ${file}${suffix}_MN*"

  if [ "$verbose" = true ] ; then
    print_files ${rm_files}
  fi

  rm ${rm_files}
done  

# Finally, remove any *lock file left in the results directory
list="$(find ${resultsDir} -name '*.lock')"
rm ${list}
