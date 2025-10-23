import numpy as np
import pandas as pd
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

all_activities = {'business', 'delivery', 'depot', 'education', 'escort_business', 'escort_education', 'escort_home', 'escort_other', 'escort_shop', 'escort_work', 'home', 'medical', 'other', 'pt interaction', 'shop', 'visit', 'work'}
all_modes = {'bike', 'bus', 'car', 'car_passenger', 'ferry', 'rail', 'subway', 'taxi', 'tram', 'walk'}
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
    
#find the change in plan utility. returns a list of the change between each of the plans in descending order
def get_delta_u_ij(utility_modes):
    delta_u_ij = []
    utility_modes = dict(sorted(utility_modes.items(), key=lambda item: item[0], reverse=True))  #is this sorting ok?
    #print(utility_modes)
    for i in range(len(utility_modes)-1):
        if list(utility_modes.keys())[i] and list(utility_modes.keys())[i+1] == 0:
            temp_u = 0
        else:
            temp_u = abs(list(utility_modes.keys())[i]-list(utility_modes.keys())[i+1])/max(abs(list(utility_modes.keys())[i]), abs(list(utility_modes.keys())[i+1]))
        delta_u_ij.append(temp_u + 1)
    return delta_u_ij

#find the change in mode across plans. compares total day plans rather than legs etc
#this function definitely needs more work to make it a more refined comparison between modes 
def get_delta_m_ij(utility_modes):
    delta_m_ij = []
    unique_m = []
    utility_modes = dict(sorted(utility_modes.items(), key=lambda item: item[0], reverse=True))  #is this sorting ok?
    append_unique = lambda lst, val: (lst.append(val) or lst) if val not in lst else lst
    for i in range(len(utility_modes)-1):
        if ((list(utility_modes.values())[i] != list(utility_modes.values())[i+1]) and (list(utility_modes.values())[i+1] not in unique_m)):
            temp_m = 1 
        else:
            temp_m = 0
        delta_m_ij.append(temp_m)
        append_unique(unique_m, list(utility_modes.values())[i]) #add the modes just considered to the list to discount them in future
        append_unique(unique_m, list(utility_modes.values())[i+1])
    return delta_m_ij

#find the change in mode across plans. compares total day plans rather than legs etc
#this function definitely needs more work to make it a more refined comparison between modes 
def get_delta_m_ij_1(modes):
    delta_m_ij = []
    unique_m = []
    #utility_modes = dict(sorted(utility_modes.items(), key=lambda item: item[0], reverse=True))  #is this sorting ok?
    append_unique = lambda lst, val: (lst.append(val) or lst) if val not in lst else lst
    for i in range(len(modes)-1):
        if (modes[i] != modes[i+1]) and (modes[i+1] not in unique_m):
            temp_m = 1 
        else:
            temp_m = 0
        delta_m_ij.append(temp_m)
        append_unique(unique_m, modes[i])#add the modes just considered to the list to discount them in future
        append_unique(unique_m, modes[i+1])
    return delta_m_ij

#find flexibility score, based on delta u and delata m as found above
def get_f_value(delta_u_ij, delta_m_ij):
    f = 0
    for i in range(len(delta_u_ij)):
        f += delta_m_ij[i]/delta_u_ij[i]  #maybe add a weighitng here too such as 1/(i+1)
    return f

#groups individual legs into split out trips. 
def group_legs_into_trips(activity_mode_list, activity_indices):
    modes = []
    for i in range(len(activity_indices)):
        if i>0:
            modes_temp = activity_mode_list[activity_indices[i-1]+1:activity_indices[i]]
            modes.append(list(modes_temp))
    return modes

#sums distance or duration of legs in each trip
def group_legs_into_trips_d_sum(distance_or_duration, activity_indices, which):
    if which == "distance":
        distance_or_duration = pd.to_numeric(distance_or_duration, errors="coerce")
    elif which == "duration":
        distance_or_duration = pd.to_timedelta(distance_or_duration, errors="coerce").seconds
    else:
        print("incorrect input")  
    values = []
    for i in range(1, len(activity_indices)):
            val_temp = sum(distance_or_duration[activity_indices[i-1]+1:activity_indices[i]])
            values.append(val_temp)
    return values

def group_legs_into_trips_d(distance_or_duration, activity_indices, which):
    values = []
    if which == "distance":
        distance_or_duration = pd.to_numeric(distance_or_duration, errors="coerce")
    elif which == "duration":
        distance_or_duration = pd.to_timedelta(distance_or_duration, errors="coerce").seconds
    else:
        print("incorrect input")  
    values = []
    for i in range(1, len(activity_indices)):
            val_temp = distance_or_duration[activity_indices[i-1]+1:activity_indices[i]]
            values.append(list(val_temp))
    return values

#count how many transfers are made in a trip
def count_transfers(modes_in_leg):
    publicTrans = ["subway","bus","rail", "tram","ferry", "pt"]
    transfers = 0
    for i in range(len(modes_in_leg)-1):
        if modes_in_leg[i] in publicTrans and modes_in_leg[i + 1] in publicTrans:
            transfers += 1
    return transfers

#calculate the utility lost across trips in a plan. returns a list of the utility from each trip
def calculate_travel_utility(trips, distances, durations, subpopulation):
    utilities = []
    betaTrans = -1
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
    for i in range(len(trips)):
        # print(trips[i])
        STotal = 0
        transferCount = count_transfers(trips[i])
        for j in range(len(trips[i])):
            # print(trips[i][j])
            # print("distance is: "+str(distances[i][j]))
            # print("duration is: "+str(durations[i][j]))
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
                        gammaDist = 0
                    # print("gamma dist: "+str(gammaDist))
                case "car_passenger":
                    CMode = -5
                    betaTrav = 0
                    betaDist = 0
                    if subpopulation in ["low","medium","high"]:
                        gammaDist = -2e-4 
                    elif subpopulation in ["ev_low","ev_medium","ev_high"]:
                        gammaDist = -5e-5 
                    else:
                        gammaDist = 0
                    
                case "walk":
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
            STime = betaTrav*(durations[i][j]/3600)
            # print("STime: "+str(STime))
            SMon = 0
            # print("Smon: "+str(SMon))
            SDist = (betaDist + (betaMon*gammaDist))*distances[i][j]
            # print("SDist: "+str(SDist))
            STotal_temp = CMode + STime + SMon + SDist 
            STotal += STotal_temp
        STrans = transferCount * betaTrans
        # print("Strans: "+str(STrans))
        STotal += STrans
        # print("STotal: "+str(STotal))
        utilities.append(STotal)
    return utilities


def get_activities(activity_modes, activity_indices):
    activities = []
    for i in activity_indices:
        activities.append(activity_modes[i])
    return activities

def get_activity_durations(activity_indices, all_durations, all_activities_trips):
    activity_start_times = []
    activity_end_times = []
    all_durations = pd.to_timedelta(all_durations, errors="coerce").seconds

    for i in range(len(activity_indices)):
        schedEndTime = all_durations[activity_indices[i]]
        if activity_indices[i]==0:
            startTime = 0
        else:
            prevEndTime = all_durations[activity_indices[i-1]]
            x1 = activity_indices[i-1]+1
            x2 = activity_indices[i]
            startTime = prevEndTime+sum(all_durations[x1:x2])  
        if startTime >= schedEndTime:
            realEndTime = startTime +1
        else:
            realEndTime = schedEndTime
        activity_start_times.append(startTime)
        activity_end_times.append(realEndTime)
    # print("start: "+str(activity_start_times))
    # print("end: "+str(activity_end_times))
    
    for i in range(1, len(activity_end_times)):
        if activity_end_times[i] < activity_end_times[i-1]:
            activity_end_times[i] += 24*3600  #account for wraparound
    # print("end new: "+str(activity_end_times))
   
    activity_durations = list(map(operator.sub, list(activity_end_times), list(activity_start_times)))
   
    if all_activities_trips[0] == all_activities_trips[-1]:
        activity_durations[0]=activity_durations[0]+((24*3600)-activity_start_times[-1]) #make it wrap around to midnight
        activity_durations.pop() #remove last activity duration as it has been included in the frist activity
    
    for k in range(len(activity_durations)):
        if activity_durations[k]== 0:
            activity_durations[k] = 1e-5
    
    return(activity_durations)     
# TODO: account for non-wraparound effect - HOW DOES THIS WORK
# TODO: when accounting for wraparound effect the final "end time" is basically ignored - is this ok?
# TODO: account for if someone arrives after departure -> set activity length to 1 second and continue on
# TODO: cutoff when not achieving full activity plan - up to 32 hours / journey longer than expected departure

def calculate_activity_utility(activities, durations):
    utilities = []
    # betaEarly = 0
    # betaLate = 0
    betaPerf = 10
    # betaWait = 0
    # betaShort = 0
    prio = 1
    durations = [a/3600 for a in durations]  #put it back into hours
    if activities[-1] == activities[0]:
        activities.pop() #remove the last activity for wraparound
    for i in range(len(activities)):
        # print(activities[i])
        # print(durations[i])
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
                print("dodgy activity type")
                tMin = np.nan
                tTyp = np.nan
        # print("tTyp: "+str(tTyp))
        t0 = tTyp*np.exp(-1/prio)
        # print("t0: "+str(t0))
        SDur = betaPerf*tTyp*np.log(durations[i]/t0)
        SWait = 0 #since betaWait is zero. Otherwise, will need to encode open/close times for activities to find out how long waiting       
        SLate = 0 #since betaLate is zero. Otherwise, will need to encode latest start times for activities to find out how late   
        SEarly = 0 #since betaEarly is zero. Otherwise, will need to encode earliest end times for activities to find out how early   
        SShort = 0 #since betaEarly is zero/undefined. Otherwise, will need to use shortesr durations for activities to find out if too short   
        STotal_temp = SDur + SWait + SLate + SEarly + SShort
        STotal += STotal_temp
        # print("STotal: "+str(STotal))
        utilities.append(STotal)
    return utilities