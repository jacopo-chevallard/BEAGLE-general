import numpy as np
from scipy import interp 

file_name = "filterfrm.res"

split_name = file_name.split(".")
output_name = split_name[0] + "_resampled." + split_name[1]

f_in = open(file_name, 'r')

f_out = open(output_name, 'w')

wl = list()
t_wl = list()

max_n_wl = 400

for line in f_in:

    if line.startswith("#"):

        if len(wl) > 1:

            np_wl = np.array(wl, dtype=np.float32)
            np_t_wl = np.array(t_wl, dtype=np.float32)
            np_t_wl /= np.amax(np_t_wl)

            np_t_wl[np_t_wl < 0.] = 0.

            sor = np.argsort(np_wl)

            np_t_wl = np_t_wl[sor]
            np_wl = np_wl[sor]

            if len(wl) > max_n_wl:
                new_wl = np.linspace(np_wl[0], np_wl[-1], max_n_wl)
                new_t_wl = interp(new_wl, np_wl, np_t_wl)
            else:
                new_wl = np_wl
                new_t_wl = np_t_wl

            for wl, t_wl in zip(new_wl, new_t_wl):
                f_out.write("{:.1f}   {:.3e} \n".format(wl, t_wl))

            f_out.write(line)

            wl = list()
            t_wl = list()

            continue

        else:
            f_out.write(line)
            wl = list()
            t_wl = list()
            continue
    
    wl_, t_wl_ = line.split()

    wl.append(wl_)
    t_wl.append(t_wl_)

# last filter
np_wl = np.array(wl, dtype=np.float32)
np_t_wl = np.array(t_wl, dtype=np.float32)
np_t_wl /= np.amax(np_t_wl)
if len(wl) > max_n_wl:
    interp = interp1d(np_t_wl, np_wl)
    new_wl = np.linspace(wl[0], wl[-1], max_n_wl)
    new_t_wl = interp(new_wl)
else:
    new_wl = np_wl
    new_t_wl = np_t_wl

for wl, t_wl in zip(new_wl, new_t_wl):
    f_out.write("{:.1f}   {:.3e} \n".format(wl, t_wl))

f_in.close()
f_out.close()

print "output_name: ", output_name
