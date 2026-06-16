import numpy as np
import pandas as pd
import math
# import geopandas as gpd
import operator

#identify which agents has any negative utility across their top 5 plans. returns 1 if there is a negative
def neg_utility_somewhere(row):
    if row["unselected plan (1) utility"] < 0:
        return 1
    elif row["unselected plan (2) utility"] < 0:
        return 1
    elif row["unselected plan (3) utility"] < 0:
        return 1
    elif row["unselected plan (4) utility"] < 0:
        return 1
    elif row["selected plan utility"] < 0:
        return 1
    else:
        return 0
    
#get the index of where pt interaction happens
def get_ptinteraction_index(item_list):
    return [i for i, val in enumerate(item_list) if val == 'pt interaction']

#remove values at the index of where pt interaction is
def remove_ptinteraction(indices, values):
 
    # Return original list if indices is empty
    if not indices:
        return values

    # Basic type check (optional but helpful)
    if not isinstance(values, list) or not isinstance(indices, list):
        raise TypeError("Both values and indices should be lists")

    return [val for i, val in enumerate(values) if i not in indices]

all_activities = {'business', 'delivery', 'depot', 'gym', 'park', 'pub', 'leisure', 'education', 'escort_business', 'escort_education', 'escort_home', 'escort_other', 'escort_shop', 'escort_work', 'home', 'medical', 'other', 'pt interaction', 'shop', 'visit', 'work'}
all_modes = {'bike', 'bus', 'car', 'car_passenger', 'ferry', 'rail', 'subway', 'taxi', 'tram', 'walk', 'pt'}
#return the indices of the activities in activity_type_or_mode 

def get_trips_indices_only(trips_and_activities):
    indices = []
    for i in range(len(trips_and_activities)):
        if trips_and_activities[i] in all_modes:
            indices.append(i)
    return indices
#return the indices of the modes in activity_type_or_mode
def get_activities_indices_only(trips_and_activities):
    indices = []
    for i in range(len(trips_and_activities)):
        if trips_and_activities[i] in all_activities:
            indices.append(i)
    return indices
#return the corresponding location/duration/activity/mode according to the index as found above
def get_trips_duration_or_mode(indices, durations_or_activities):
    outputs = []
    for i in indices:
        outputs.append(durations_or_activities[i])
    return outputs

# keep only the indices in the activity/leg list which correspond to activities and the longest leg of each trip
# activities can be identified by having N/A distance 
# the longest leg is the longest non-NA distance between each N/A
def filter_max_between_nas_indices_only(lst):
    if not isinstance(lst, list):
        # print(lst)
        # print("error1")
        return []
        
        # raise TypeError(f"Expected a list, got {type(lst)}")

    kept_indices = []    # Indices of values to keep
    buffer = []          # Temporarily holds float values between "N/A"s
    buffer_indices = []  # Their original indices

    for i, val in enumerate(lst):
        if isinstance(val, list):
            raise TypeError(f"Unexpected nested list at index {i}: {val}")

        if val == "N/A":
            # If there is a buffer of float values, keep the max one
            if buffer:
                max_val = max(buffer)
                max_index = buffer_indices[buffer.index(max_val)]
                kept_indices.append(max_index)
                buffer = []
                buffer_indices = []

            # Always keep the index of "N/A"
            kept_indices.append(i)

        else:
            try:
                float_val = float(val)
                buffer.append(float_val)
                buffer_indices.append(i)
            except ValueError:
                raise ValueError(f"Non-numeric value encountered (not 'N/A'): {val}")

    # Handle remaining buffer if list does not end in "N/A"
    if buffer:
        max_val = max(buffer)
        max_index = buffer_indices[buffer.index(max_val)]
        kept_indices.append(max_index)

    return kept_indices

#return a set of unique modes used in the plan
def get_unique_modes(lst):
    if not isinstance(lst, list):
        return []
    lst_modes_unique = set()
    for i in lst:
        if i in all_modes:
            lst_modes_unique.add(i)
    return lst_modes_unique

#check if an individual is car dependent. returns 1 if they use only cars in all of their top plans
car_modes = {"car", "car_passenger"}
def get_car_only(modes):
    mode_set = set.union(*modes)
    if mode_set.issubset(car_modes):
        return 1
    else:
        return 0
    

def group_routes_into_trips(routes_list, activity_indices, stuck_id):
    routes_all = []
    for i in range(len(activity_indices)):
        if (i > 0) and (activity_indices[i] < stuck_id - 1):
            route_segment = routes_list[activity_indices[i-1]+1 : activity_indices[i]]
            # Keep as a list of strings, one per leg — do NOT join into one string
            routes_all.append([str(r) for r in route_segment])
    return routes_all

def group_legs_into_trips(activity_mode_list, activity_indices, stuck_id):
    modes = []
    for i in range(len(activity_indices)):
        if (i>0) and (activity_indices[i]<stuck_id-1):
            modes_temp = activity_mode_list[activity_indices[i-1]+1:activity_indices[i]]
            modes.append(list(modes_temp))
    return modes

def group_legs_into_trips_d(distance_or_duration, activity_indices, stuck_id, which):
    values = []
    if which == "distance":
        distance_or_duration = pd.to_numeric(distance_or_duration, errors="coerce")
    elif which == "duration":
        distance_or_duration = pd.to_timedelta(distance_or_duration, errors="coerce").total_seconds()
    else:
        print("incorrect input")  
    values = []
    for i in range(1, len(activity_indices)):
            if activity_indices[i] < stuck_id-1:
                val_temp = distance_or_duration[activity_indices[i-1]+1:activity_indices[i]]
                values.append(list(val_temp))
    return values

#count how many transfers are made in a trip
def count_transfers(modes_in_leg):
    publicTrans = ["subway","bus","rail", "tram","ferry", "pt"]
    transfers = 0
    for i in range(len(modes_in_leg)-1):
        if (modes_in_leg[i] in publicTrans and modes_in_leg[i + 1] in publicTrans) :
            transfers += 1
    for j in range(len(modes_in_leg)-2):
        if (modes_in_leg[j] in publicTrans and modes_in_leg[j + 2] in publicTrans and modes_in_leg[j+1]=="walk") :
            transfers += 1
    return transfers

def calculateWaitingToBoardTime(activity_ends, total_durations, activity_indices, boardingTime, stuck_id):
    durations = group_legs_into_trips_d(total_durations, activity_indices, stuck_id, "duration")
    bt_trips = group_legs_into_trips_d(boardingTime, activity_indices, stuck_id, "duration")
    
    trip_ends_full = []
    wait_times_full = []

    for i in range(len(durations)):
        starttimecounter = float(activity_ends[i])
        trip_ends = []
        
        for j in range(len(durations[i])):
            if j == 0:
                trip_ends.append(starttimecounter)
            else:
                starttimecounter+=float(durations[i][j-1])
                trip_ends.append(starttimecounter)
       
        trip_ends_full.append(trip_ends)
        waitingTimes  = list(map(operator.sub, list(bt_trips[i]), list(trip_ends)))
        wait_times_full.append(waitingTimes)
        
    return(wait_times_full)

#calculate the utility lost across trips in a plan. returns a list of the utility from each trip
def calculate_travel_utility(id, total_activities_modes, total_durations, total_distances, activity_indices, subpopulation, boardingTime, activity_ends, routes, tolls, stuck_id):
    
    boardWait = calculateWaitingToBoardTime(activity_ends, total_durations, activity_indices, boardingTime, stuck_id)
    trips = group_legs_into_trips(total_activities_modes, activity_indices, stuck_id)
    durations = group_legs_into_trips_d(total_durations, activity_indices, stuck_id, "duration")
    distances = group_legs_into_trips_d(total_distances, activity_indices, stuck_id, "distance")
    routes = list(routes)
    routes = group_routes_into_trips(routes, activity_indices, stuck_id)

    utilities = []
    total_row_toll_value = 0.0
    total_row_toll_count = 0
    betaTrans = -1
    betaWait = 0
    match subpopulation:
        case "low":
            betaMon = 2
        case "medium":
            betaMon = 1
        case "high":
            betaMon = 0.5
        case "ev_low":
            betaMon = 2
        case "ev_medium":
            betaMon = 1
        case "ev_high":
            betaMon = 0.5
        case _:
            print("dodgy subpopulation")
            betaMon = 1
    
    totalTransferCount = 0
    for i in range(len(trips)):
        STotal = 0
        transferCount = count_transfers(trips[i])
        totalTransferCount+=transferCount
        modes_seen_in_trip = set()
        for j in range(len(trips[i])):
            match trips[i][j]:
                case "car":
                    CMode = -5
                    betaTrav = 0
                    betaDist = 0
                    if subpopulation in ["low","medium","high"]:
                        gammaDist = -2e-4 
                    elif subpopulation in ["ev_low","ev_medium","ev_high"]:
                        gammaDist = -5e-5 
                    else:
                        print("dodgy subpopulation car")
                        gammaDist = -9.0E-5
                case "car_passenger":
                    CMode = -5
                    betaTrav = 0
                    betaDist = 0
                    if subpopulation in ["low","medium","high"]:
                        gammaDist = -2e-4 
                    elif subpopulation in ["ev_low","ev_medium","ev_high"]:
                        gammaDist = -5e-5 
                    else:
                        print("dodgy subpopulation car passenger")
                        gammaDist = -9.0E-5
                    
                case "walk"| "non_network_walk" | "transit_walk" | "access_walk" | "egress_walk":
                    CMode = 0
                    betaTrav = 0
                    betaDist = -0.003
                    gammaDist = 0
                    
                case "bike":
                    CMode = -4
                    betaTrav = 0
                    betaDist = -0.0015
                    gammaDist = 0
                    
                case "bus":
                    CMode = -1
                    betaTrav = 0
                    betaDist = 0
                    gammaDist = -1.7e-4
                    
                case "tram":
                    CMode = 0
                    betaTrav = 0
                    betaDist = 0
                    gammaDist = -4e-4
                    
                case "rail":
                    CMode = -8
                    betaTrav = -0.5
                    betaDist = 0
                    gammaDist = -2e-4
                    
                case "taxi":
                    CMode = -5
                    betaTrav = 0
                    betaDist = 0
                    gammaDist = -0.002
                 
                case "ferry":
                    CMode = 0
                    betaTrav = 0
                    betaDist = 0
                    gammaDist = -0.001
                 
                case "subway":
                    CMode = 0
                    betaTrav = 0
                    betaDist = 0
                    gammaDist = -2e-4
                case _:
                    print("dodgy travel mode type")
                    CMode = 0
                    betaTrav = 0
                    betaDist = 0
                    gammaDist = 0
            if trips[i][j] in modes_seen_in_trip:
                CMode = 0  # Mode already used in this trip, set constant to 0
            else:
                modes_seen_in_trip.add(trips[i][j])

            STime = betaTrav*(durations[i][j]/3600)

            try:         
                leg_toll_val, leg_toll_count = assign_tolls(tolls, routes[i][j], trips[i][j], distances[i][j])
                total_row_toll_value += leg_toll_val
                total_row_toll_count += leg_toll_count
                tollcost = -1 * leg_toll_val
            except Exception as e:
                print(f"Tolls failed for {id}: {e}")
                tollcost = 0
            SMon = betaMon * tollcost
            SDist = (betaDist + (betaMon*gammaDist))*distances[i][j]
            if pd.isna(boardWait[i][j]):
                boardWait_s = 0
            else:
                boardWait_s = boardWait[i][j]
            SWait = (betaWait - betaTrav) * (boardWait_s / 3600)
            STotal_temp = CMode + STime + SMon + SDist + SWait
            STotal += STotal_temp
        STrans = transferCount * betaTrans 
        STotal += STrans
        if not math.isfinite(STotal):
            print(id)
        utilities.append(STotal)
    return pd.Series([utilities, total_row_toll_value, total_row_toll_count, totalTransferCount])


def get_activities(activity_modes, activity_indices, stuck_index):
    activities = []
    for i in activity_indices:
        if i<stuck_index:
            activities.append(activity_modes[i])
    return activities


def _get_opening_hours(activity_type):
    match activity_type:
        case "home":             return (0, 115200)
        case "work":             return (7*3600, 19*3600+30*60)
        case "other":            return (0, 115200)
        case "shop":             return (8*3600+30*60, 19*3600+30*60)
        case "education":        return (8*3600+30*60, 17*3600)
        case "visit":            return (0, 115200)
        case "medical":          return (9*3600, 18*3600)
        case "business":         return (7*3600+30*60, 20*3600)
        case "escort_home":      return (0, 115200)
        case "escort_work":      return (7*3600, 19*3600+30*60)
        case "escort_business":  return (7*3600, 19*3600+30*60)
        case "escort_education": return (8*3600+30*60, 17*3600)
        case "escort_other":     return (0, 115200)
        case "escort_shop":      return (8*3600+30*60, 17*3600+30*60)
        case _:
            print("dodgy activity type: "+str(activity_type))
            return (np.nan, np.nan)



def opening_times_adjust(activities, activity_start_times, activity_end_times):
    new_ast = []
    new_aet = []
    for i in range(len(activities)):
    
        if (activity_end_times[i] - activity_start_times[i] <= 1.0) and (i < len(activities)-1):
            # It's missed. Bypass opening hours so it retains its 1s duration and gets penalized
            new_ast.append(activity_start_times[i])
            new_aet.append(activity_end_times[i])
            continue
        open, close = _get_opening_hours(activities[i])

        if (activity_start_times[i]<open) & (activity_end_times[i]<=open):
            new_ast.append(open)
            new_aet.append(open)

        elif (activity_start_times[i]<open) & (activity_end_times[i]>open) & (activity_end_times[i]<close):
            new_ast.append(open)
            new_aet.append(activity_end_times[i])

        elif (activity_start_times[i]>open) & (activity_start_times[i]<close) & (activity_end_times[i]>open) & (activity_end_times[i]<close):
            new_ast.append(activity_start_times[i])
            new_aet.append(activity_end_times[i])
        
        elif (activity_start_times[i]>open) & (activity_start_times[i]<close) & (activity_end_times[i]>close):
            new_ast.append(activity_start_times[i])
            new_aet.append(close)
        
        elif (activity_start_times[i]>close) & (activity_end_times[i]>close):
            new_ast.append(close)
            new_aet.append(close)

        elif (activity_start_times[i]<open) & (activity_end_times[i]>close):
            new_ast.append(open)
            new_aet.append(close)
        
        
        else:
            new_ast.append(activity_start_times[i])
            new_aet.append(activity_end_times[i])

    return(new_ast, new_aet)


def get_activity_timings(activity_indices, all_durations, all_activities_trips, stuck_bool):

    activity_start_times = []
    activity_end_times = []
    all_durations = pd.to_timedelta(all_durations, errors="coerce").total_seconds() 

    stuck_index = activity_indices[-1] + 2  # default: no stuck, all activities valid
    
    for i in range(len(activity_indices)):
        schedEndTime = all_durations[activity_indices[i]]
        if activity_indices[i]==0:
            startTime = 0
        else:
            prevEndTime = all_durations[activity_indices[i-1]]
            x1 = activity_indices[i-1]+1
            x2 = activity_indices[i]
            startTime = prevEndTime+sum(all_durations[x1:x2]) 

        # Activity starts after the 32-hour simulation cutoff:
        # agent was stuck in the preceding trip and reverted to the previous activity
        if startTime >= 32 * 3600:
            stuck_index = activity_indices[i]      # this activity and beyond are excluded
            break
        if startTime >= schedEndTime:
            realEndTime = startTime +1
        else:
            realEndTime = schedEndTime
        activity_start_times.append(startTime)
        activity_end_times.append(realEndTime)

    if (stuck_index == activity_indices[-1]+2) & (stuck_bool == 0): #so this is for non-wrap, non-stuck agents
        activity_end_times[-1] = 24*3600 #set non-wraparound activities to end at midnight

    activities = get_activities(all_activities_trips, activity_indices, stuck_index)

    new_activity_start_times, new_activity_end_times = opening_times_adjust(activities, activity_start_times, activity_end_times)

    return(new_activity_start_times, new_activity_end_times, stuck_index) 


def get_activity_durations(activity_starts, activity_ends, all_activities_trips, stuck_index, stuck_bool):

    activity_durations = list(map(operator.sub, list(activity_ends), list(activity_starts)))
    
    wraparound_negative = False
    if (all_activities_trips[0] == all_activities_trips[-1]) & (stuck_index > len(all_activities_trips)) & (stuck_bool == 0):
        open_h, close_h = _get_opening_hours(all_activities_trips[0])
        if open_h > 0 or close_h < 86400:
            activity_durations[0] = activity_durations[-1]
        else:
            activity_durations[0] = activity_durations[0] + activity_durations[-1]
        activity_durations.pop()
        if activity_durations[0] < 0:
            wraparound_negative = True

    activity_durations = [
        v if (i == 0 and wraparound_negative) or (i == len(activity_durations) - 1 and v < 0)
        else max(1, v)
        for i, v in enumerate(activity_durations)
    ]

    return activity_durations

def calculate_activity_utility(activity_modes, activity_indices, stuck_index, durations, stuck_bool):
    activities = get_activities(activity_modes, activity_indices, stuck_index)
    utilities = []
    betaPerf = 10 
    # betaWait = 0
    # betaShort = 0
    prio = 1
    durations = [a/3600 for a in durations]  #put it back into hours

    if (activities[-1] == activities[0]) & (stuck_index > len(activity_modes)) & (stuck_bool == 0): #remove final activity for wraparound non-stuck agents
        activities.pop() 
    for i in range(len(activities)):
        STotal = 0
        match activities[i]:
            case "home":
                tMin = 1
                tTyp = 10
            case "work":
                tMin = 6
                tTyp = 9
            case "other":
                tMin = 1/6
                tTyp = 0.5
            case "shop": 
                tMin = 0.5
                tTyp = 0.5
            case "education":
                tMin = 6
                tTyp = 6
            case "visit":
                tMin = 0.5
                tTyp = 2
            case "medical":
                tMin = 0.5
                tTyp = 1
            case "business":
                tMin = 0.5
                tTyp = 1
            case "escort_home":
                tMin = 1/12
                tTyp = 1/12
            case "escort_work":
                tMin = 1/12
                tTyp = 1/12
            case "escort_business":
                tMin = 1/12
                tTyp = 1/12
            case "escort_education":
                tMin = 1/12
                tTyp = 1/12
            case "escort_other":
                tMin = 1/12
                tTyp = 1/12
            case "escort_shop":
                tMin = 1/12
                tTyp = 1/12      
            case _:
                print("dodgy activity type: "+str(activities[i]))
                tMin = np.nan
                tTyp = np.nan
        t0 = tTyp*np.exp(-1/prio)
        if durations[i]> t0:
            SDur = betaPerf*tTyp*np.log(durations[i]/t0)
        else: 
            SDur = -1* betaPerf*tTyp/t0*(t0-durations[i])
        SWait = 0 #since betaWait is zero. Otherwise, will need to encode open/close times for activities to find out how long waiting       
        SLate = 0 #since betaLate is zero. Otherwise, will need to encode latest start times for activities to find out how late   
        SEarly = 0 #since betaEarly is zero. Otherwise, will need to encode earliest end times for activities to find out how early   
        SShort = 0 #since betaEarly is zero/undefined. Otherwise, will need to use shortesr durations for activities to find out if too short   
        STotal_temp = SDur + SWait + SLate + SEarly + SShort
        STotal += STotal_temp
        utilities.append(STotal)
    return utilities


def assign_tolls(tolls, route, mode, distance):
    toll_sum_temp = 0.0
    toll_count = 0
    route_list = route.split(' ')
    if mode in ["car", "taxi"] and isinstance(route, str) and distance>0: # Safety check for route strings
        for link_id in route_list[1:]: #TODO: BUT THIS MAY MISS A TOLL THAT COULD BE ON THE LAST LINK OF THE LAST LEG IF FIRST AND LAST LOC ARE NOT IN THE SAME PLACE.
            if link_id and link_id != "N/A":
                try:
                    val = float(tolls[link_id])
                    if val != 0:
                        toll_sum_temp += val
                        toll_count += 1
                except (KeyError, ValueError):
                    pass 
    return toll_sum_temp, toll_count


def calculate_stuck_penalty(stuck_bool, stuck_index, activity_modes):
    if (stuck_bool == 1) | (stuck_index < len(activity_modes)):
        penalty = -24*10.5 # hard coded from the data for ease atm
    else:
        penalty = 0
    return penalty

