''' Notes for V15: introduced loading the intervals generated using pickle to ensure consistency with the solutions. Running the intervals.py script every time we solve the problem gives different number of intervals (+-2 for some bizarre reason) giving different optimal solutions. If the number of intervals is larger, even by a small amount, the objVal differs signficantly as we are able to perform more maintenance and hence more planes at the end of the planning horizon are over the 0.4 service level agreement. '''

'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~GLOBAL ENVIRONMENT CALLS~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''
from gurobipy import *
scriptpath = "../../flightradar24/v16"
sys.path.append(os.path.abspath(scriptpath))
from intervals import *       ##  Imports classes and functions defined in intervals.py  ##

'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Simple Functions~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''

def load_intervals():
    '''Simple loading function that loads the output of intervals.py from the directory specified below. Intervals are loaded using pickle which preserves the class properties.'''
    import os
    import sys
    import pickle

    IntervalObject = open(scriptpath + '/output/intervals.p','r')
    AircraftObject = open(scriptpath + '/output/aircraft_list.p','r')
    intervals = pickle.load(IntervalObject)
    aircraft_list = pickle.load(AircraftObject) # gets input from 'intervals.py' in v15
    IntervalObject.close()
    AircraftObject.close()
    return intervals, aircraft_list

def get_solutions(d, m, C, keys, aircraft_list):
    '''Extract solution values for performance d, maintenance m, and number of planes over the service level (0.4) C '''
    d_v, m_v, C_v = {}, {}, {}
    d_v = {k: float(v.x) for k,v in d.iteritems() if any(k == key for key in keys)}
    m_v = {k: float(v.x) for k,v in m.iteritems() if v.x > 3e-12 and
           any(k[0] == key[0] and k[1] == key[1] for key in keys)}
    C_v = {k: float(v.x) for k,v in C.iteritems() if v.x ==1 and any(k == key for key in aircraft_list)}
    return d_v, m_v, C_v

def get_constants(intervals):
    '''Loads PARAMETERS and CONSTANTS '''
    import time
    ## Rates ##
    r = [5.4e-8, 5.4e-8] # Improvement rate on perfomance measure for A r[0], or C r[1]
    w = - 1e-8           # Degradation rate for flight operation
    n = len(intervals)
    check_t = ['A','C']  # Check Types
    ## Interval Times ##
    t = [int(time.mktime(intervals[i].start_t.timetuple())) for i in range(n)]
    t.append(int(time.mktime(intervals[-1].end_t.timetuple()))) # End of planning horizon
    ## Resources ##
    resources_list = ['r1', 'r2', 'r3', 'r4'] # Resource labels
    b = {('r1','A') : 1, ('r2','A') : 2, ('r3', 'A') : 1, ('r4','A') : 1, ('r1','C') : 1, ('r2','C') : 1, ('r3','C') : 1, ('r4', 'C') : 2}# Resource demands
    B = {'r1':1,'r2':2,'r3':1,'r4':2}         # Resouce capacities
    return r, w, n, check_t, t, resources_list, b, B

def create_variables(model, aircraft_dict, check_t, n):
    '''Generate variables from aircraft dictionary '''
    d, m, C = {}, {}, {}
    d = model.addVars([(i,k) for k, v in aircraft_dict.iteritems() for i in v],
                      vtype = "C", lb = 0.2, ub = 1.0, name = "d")
    m = model.addVars([(i,k,c) for k, v in aircraft_dict.iteritems() for i in v
                       for c in check_t], vtype = "B", name = "m")
    C = model.addVars([k for k in aircraft_dict.keys()], vtype = "B", name = "C")
    model.update()
    return model, d, m, C

def fill_performance_dict(n = 0, d_dict = {}, keys = [], w = 0, t = []):
    '''Using the performance solutions, we fill in for the variables not created for the lp.'''
    dict_fill = {}
    new_aircraft_list = list(set(key[1] for key in keys))
    for plane in new_aircraft_list:
        for i in range(1,n+1):
            if (i,plane) in d_dict.keys():
                dict_fill[(i,plane)] = float(d_dict[(i,plane)])
            elif i-1 == 0:
                dict_fill[(i,plane)] = 0.4
            else:
                dict_fill[(i,plane)] = dict_fill[(i-1,plane)] + w*(t[i] - t[i-1])
    return dict_fill

def intervals_per_plane(intervals = [], aircraft_list = []):
    ''' Preprocess dictionary to include first and last interval and eliminate the entries where no maintenance is being performed '''
    aircraft_dict = {k : [] for k in aircraft_list}
    n = len(intervals)
    for i in range(1,n):
        for k in intervals[i].aircraft_l:
            aircraft_dict[k].append(i)
    aircraft_dict = {k : v for k, v in aircraft_dict.iteritems() if len(v) != 0}
    
    final_list = []
    if len(aircraft_list) > len(aircraft_dict.keys()):
        final_list = [k for k in aircraft_dict.keys()]
        aircraft_dict = {k : v for k, v in aircraft_dict.iteritems()}

    final_dict = {}
    for k,v in aircraft_dict.iteritems():
        aircraft_dict[k].append(0)
        aircraft_dict[k].append(n)
        final_dict[k] = sorted(v)
        final_dict[k] = list(set(v)) # Removes duplicates
    return final_dict, final_list

def intervals_per_station(intervals, aircraft_list, station):
    new_intervals = [interval for interval in intervals if interval.station == station]
    keys = [(intervals.index(interval),k) for interval in new_intervals
            for k in interval.aircraft_l]
    keys_0 = list(set((0,key[1]) for key in keys))
    keys_n = list(set((len(intervals),key[1]) for key in keys))
    keys.extend((keys_0, keys_n))
    return new_intervals, keys

'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~Cool Functions~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''

def sensitivity(model,resources, n):
    ''' Gets slack values for each of the resource constraints '''
    # model.printAttr(['ConstrName', 'Slack'])
    slack = model.getAttr("Slack", model.getConstrByName("Resources*"))
    slack = slack[-len(resources)*n:]
    return slack
        
def optimise_and_save(model, d, m, C, aircraft_dict, aircraft_list, intervals, rate, w = 0, n = 0, t = [], b = {}, B = {}, resources_list = [], check_t = []):
    '''Optimises and calls plotting routine'''
    from plotting import plot_pm_resources # Import function from plotting.py
    ## OPTIMISE ##
    model.optimize()
    maint_sites = list(set(interval.station for interval in intervals))
    ## Get solutions and plot by maintenance location ##
    for station in maint_sites:
        print "Gathering data for " + station
        intervals_station, keys = intervals_per_station(intervals, aircraft_list, station)
        aircraft_list_station = list(set(key[1] for key in keys))
        performance_v, maintenance_v, service_level_v = get_solutions(d, m, C, keys, aircraft_list_station)
        # performance_extended = fill_performance_dict(n, performance_v, keys, w, t)
        ## PLOT ##
        print "Plotting " + station
        plot_pm_resources(station, performance_v, maintenance_v, t, aircraft_list_station, intervals, intervals_station, b, B, resources_list, check_t, w, rate, len(service_level_v.keys()))
        print "Plot saved in /output/"
    return

def formulation(model, intervals = [], aircraft_list = [], aircraft_dict = {}):
    '''Formulate model according to formulation v5.pdf '''
    import random
    ## CONSTANTS ##
    r, w, n, check_t, t, resources_list, b, B = get_constants(intervals)
    ## VARIABLES ##
    model, d, m, C = create_variables(model, aircraft_dict, check_t, n)
    ## INITIALISATIONS ##
    for k, v in aircraft_dict.iteritems(): # Performance Measure - d
        model.addConstr(d[n,k] >= 0.4*C[k] , name = "ServiceLevel_c[%s]"%(k))
        model.addConstr(d[0,k] == random.uniform(0.4,0.4), name = "Initialisation_d[%s]"%(k))
        model.addConstrs((m[0,k,c] == 0 for c in check_t), name = "Initialisation_m[%s]"%(k))
    model.update()
    ## OBJECTIVE FUNCTION ##
    coef = [1 for k in aircraft_dict.keys()]
    var = [C[k] for k in aircraft_dict.keys()]
    model.setObjective(LinExpr(coef,var),-1)
    model.update()
    ## CONSTRAINTS ##
    for k, v in aircraft_dict.iteritems():
        for i_prevs, i, i_next in previous_and_next(v):
            if i_prevs is None: # First interval (None, i, i_next)
                i_prevs = 0
            elif i_next is None or i_next == n or i == n: # Last interval
                model.addConstr(d[n,k] <= d[i_prevs, k] + w * (t[-1] - t[i_prevs]), name = "PerformanceEnd[%s,%s]"%(i,k))
                break
            model.addConstr(d[i,k] <= d[i_prevs, k] + (t[i] - t[i_prevs])*(m[i_prevs,k,'A']*r[0] + m[i_prevs,k,'C']*r[1]) + w * (t[i] - t[i_prevs])*(1 - m[i_prevs,k,'A'] - m[i_prevs,k,'C']), name = "PerformanceGain/Loss[%s,%s]"%(i,k))
            model.addConstr(m[i,k,'A'] + m[i,k,'C'] <= 1, name="4.1s")
            model.addConstr(d[i_next,k] >= 0.2, name = "PrereqFlight[%s,%s]"%(i,k))
    model.update()
    ## Resources ##
    for i in range(1,n):
        for res in resources_list:
            coef_d = [b[(res,c)] for c in check_t for k in intervals[i].aircraft_l]
            var_d = [m[i,k,c] for c in check_t for k in intervals[i].aircraft_l]
            model.addConstr(LinExpr(coef_d, var_d), "<=", B[res], name = "Resources[%s,%s]"%(res,i))
    model.update()
    ## OPTIMISE ##
    optimise_and_save(model, d, m, C, aircraft_dict, aircraft_list, intervals, r, w, n, t, b, B, resources_list, check_t)
    return

'''~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~MAIN~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'''

def main():
    import time
    start = time.time()
    time_intervals, aircraft_list = load_intervals()
    aircraft_dict, aircraft_list = intervals_per_plane(time_intervals, aircraft_list)
    model = Model("Interval-Formulation-v5")
    model.setParam('MIPFocus', 1)
    formulation(model, time_intervals, aircraft_list, aircraft_dict)
    print str((time.time()-start)/60)+ " minutes to run the whole routine"
    return

if __name__ == '__main__':
    main()
