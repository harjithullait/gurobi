'''Notes for v15: TO DO: (1) reduce the interval axis to pack all the maintenance for that specific station. One way of doing this would be to use the intervals per station, plot the length of these as the x-axis and then label them according to the values in the list. (2) plot a legend on the far right as a subplot spanning the whole 5 subplots vertically.'''

'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~GLOBAL ENVIRONMENT CALLS~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
import matplotlib.patches as patches
import matplotlib.ticker as ticker

'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Simple Functions~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''

def dict_to_arrs(maintenance_dict, interval_ids, check_type, aircraft_list):
    '''Returns numpy arrays of for the intervals where maintenance of type 'check_type' is being performed, together with the aircraft is being performed on. Additionally gives the interval shift vector for plotting.'''
    maint_dict = {key : round(v,1) for key, v in maintenance_dict.iteritems()
                  if key[2] == check_type} # key is a tuple (i,k,\tau)
    maint_list = sorted(maint_dict.keys(), key = lambda x: x[0]) # list of [(key,value),...]
    k_arr, i_arr, i_arr_shift = [], [], []
    if len(maint_list) == 0:
        print "No maintenance of type " + check_type + " has been scheduled"
    else:
        k_arr = np.array([aircraft_list.index(k[1]) for k in maint_list])
        i_arr = np.array([interval_ids.index(k[0]) for k in maint_list]) - 1 
        i_arr_shift = np.array([i+1 for i in i_arr])
    return k_arr, i_arr, i_arr_shift

def get_patches(resource, interval_ids, maintenance_dict, n, b, check_t, cmap, color_index):
    '''Generates a list of rectangular patches of the required dimensions for a given resource and check type '''
    patches_list = []
    height_list = [0]
    for i in range(1,n):
        height = 0
        sub_dict = {key : round(v,1) for key, v in maintenance_dict.iteritems()
                    if key[0] == interval_ids[i]}
        if len(sub_dict) == 0:
            continue
        else:
            for c in check_t:
                height = height + sum(v for k,v in sub_dict.iteritems() if k[2] == c)*b[(resource,c)]
            patches_list.append(patches.Rectangle((i-1, 0), 1, height, color = cmap(color_index)))
            height_list.append(height)
    return patches_list, max(height_list)

def get_cmap(n, name='hsv'):
    '''Returns a function that maps each index in 0, 1, ..., n-1 to a distinct 
    RGB color; the keyword argument name must be a standard mpl colormap name.'''
    return plt.cm.get_cmap(name, n)

def get_slack_dict(slack_list, resources, n):
    slack_dict = {}
    count = 0
    for i in range(n):
        for r in resources:
            slack_dict[(r,i)] = round(slack_list[count],1)
            count = count + 1
    return slack_dict

# def intervals_plane(plane, intervals_station):
#     intervals = []
#     count = 0
#     for k in performance_tuples_list:
#         if k[0][1] == plane and :
#             intervals.append(count)
#     return interval


'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Cool Functions~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''

def plot_pm_resources(station, performance_dict, maintenance_dict, t, aircraft_list, intervals, intervals_station, b, B, resources_list, check_t, w, rate, objVal_station):
    '''Combines performance measure function with the resource availability and usage in a single plot with shared x-axis. The x-axis is the interval number which allows one to see the evolution and interaction of all the factors.'''
    from matplotlib.transforms import Bbox
    M = len(aircraft_list)
    n = len(intervals_station)
    performance_tuples_list = sorted(performance_dict.items(), key = lambda x: x[0])
    my_xticks = [interval.i_d for interval in intervals_station]
    cmap = get_cmap(M) # Colouring function for each aircraft
    ################
    ## First Plot ##
    ################
    f, axarr = plt.subplots(3+len(resources_list), sharex=True)
    plt.tight_layout()
    for plane in aircraft_list:
        performance_plane = [k[1] for k in performance_tuples_list if k[0][1] == plane]
        intervals_plane = [my_xticks.index(k[0][0]) for k in performance_tuples_list if k[0][1] == plane]
        axarr[0].plot(intervals_plane, performance_plane, color = cmap(aircraft_list.index(plane)))
    axarr[0].set_xlim([0,n])
    axarr[0].set_title('%s %s/%s planes over the threshold w = %s, r = %s'%(station, objVal_station, M, w, rate[0]))
    ##     Grid     ##
    # Set ticks labels for x-axis
    axarr[0].set_xticks(np.arange(0,n,10))
    axarr[0].set_xticklabels(my_xticks)
    axarr[0].grid(which='both')
    ##      Service Level threshold     ## 
    axarr[0].axhline(y=.4,ls = '--', color = 'r')
    #################
    ## Second Plot ##
    #################
    axarr[1].set_title('Check Type A')
    axarr[1].set_xticks(np.arange(0,n,10))
    axarr[1].set_xticklabels(my_xticks)
    axarr[1].set_ylabel('Aircraft ID')
    axarr[1].set_yticks(np.arange(2,len(aircraft_list),2))
    axarr[1].set_yticklabels(aircraft_list, fontsize=5)
    for axis in [axarr[1].xaxis, axarr[1].yaxis]:
        axis.set_major_locator(ticker.MaxNLocator(integer=True))
    axarr[1].grid(which='both')             
    A_k, A_i, A_i_shift = dict_to_arrs(maintenance_dict, my_xticks, 'A', aircraft_list)
    axarr[1].hlines(A_k, A_i, A_i_shift, color = cmap(A_k))
    ################
    ## Third Plot ##
    ################
    axarr[2].set_title('Check Type C')
    axarr[2].set_ylabel('Aircraft ID')
    axarr[2].set_yticks(np.arange(2,len(aircraft_list),2))
    axarr[2].set_yticklabels(aircraft_list, fontsize=5)
    for axis in [axarr[2].xaxis, axarr[2].yaxis]:
        axis.set_major_locator(ticker.MaxNLocator(integer=True))
    axarr[2].set_xticks(np.arange(0,n,10))
    axarr[2].set_xticklabels(my_xticks)
    axarr[2].grid(which='both')
    C_k, C_i, C_i_shift = dict_to_arrs(maintenance_dict, my_xticks, 'C', aircraft_list)
    axarr[2].hlines(C_k, C_i, C_i_shift, color = cmap(C_k))
    #################
    ##  RESOURCES  ##
    #################
    cmap = get_cmap(2*len(resources_list))
    i = 3 # from the third subplot 
    for r in resources_list:
        ## r-th PLOT ##
        axarr[i].set_title('Resource '+ r)
        patches_list, max_height = get_patches(r, my_xticks, maintenance_dict, n, b, check_t, cmap, i)
        for axis in [axarr[i].xaxis, axarr[i].yaxis]:
            axis.set_major_locator(ticker.MaxNLocator(integer=True))
        axarr[i].set_ylim([0,max_height+1]) # Height of plot is the height of largest Rectangle in list
        ## PLOT ##
        for p in patches_list:
            axarr[i].add_patch(p) # Plot each Rectangle
        ## Grid ##                                               
        axarr[i].set_xticks(np.arange(0,n,10))
        axarr[i].set_xticklabels(my_xticks)
        axarr[i].grid(which='both')
        i = i + 1 # Next subplot down
    axarr[-1].set_xlabel('interval')

    fig = plt.gcf()
    fig.set_size_inches(11.7, 8.3)
    plt.savefig('./output/pm_resources_'+ station + '.eps', dpi=1000, orientation='portrait', papertype='a4', format='eps')
    return
