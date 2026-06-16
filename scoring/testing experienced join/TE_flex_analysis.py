import ast
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


def group_routes_into_trips(routes_list, activity_indices, stuck_id):
    if isinstance(activity_indices, str):
        activity_indices = ast.literal_eval(activity_indices)
    activity_indices = [int(x) for x in activity_indices]
    stuck_id = int(stuck_id)
    routes_all = []
    for i in range(len(activity_indices)):
        if (i > 0) and (activity_indices[i] < stuck_id - 1):
            route_segment = routes_list[activity_indices[i-1]+1 : activity_indices[i]]
            # Keep as a list of strings, one per leg — do NOT join into one string
            routes_all.append([str(r) for r in route_segment])
    return routes_all

def group_legs_into_trips(activity_mode_list, activity_indices, stuck_id):
    if isinstance(activity_mode_list, str):
        activity_mode_list = ast.literal_eval(activity_mode_list)
    if isinstance(activity_indices, str):
        activity_indices = ast.literal_eval(activity_indices)
    activity_indices = [int(x) for x in activity_indices]
    stuck_id = int(stuck_id)
    modes = []
    for i in range(len(activity_indices)):
        if (i>0) and (activity_indices[i]<stuck_id-1):
            modes_temp = activity_mode_list[activity_indices[i-1]+1:activity_indices[i]]
            modes.append(list(modes_temp))
    return modes

def group_legs_into_trips_d(distance_or_duration, activity_indices, stuck_id, which):
    if isinstance(activity_indices, str):
        activity_indices = ast.literal_eval(activity_indices)
    activity_indices = [int(x) for x in activity_indices]
    stuck_id = int(stuck_id)
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
    # print(boardingTime)
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
#TODO: add boarding time and activity ends into calls
def calculate_travel_utility(id, total_activities_modes, total_durations, total_distances, activity_indices, subpopulation, boardingTime, activity_ends, routes, tolls, stuck_id):
    
    # print(id)
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
    # match subpopulation:
    #     case "low income":
    #         betaMon = 1
    #     case "medium income":
    #         betaMon = 1
    #     case "high income":
    #         betaMon = 1
    #     case _:
    #         print("dodgy subpopulation")
    #         betaMon = 1
    totalTransferCount = 0
    for i in range(len(trips)):
        # print(trips[i])
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
            # match trips[i][j]:
            #     case "car":
            #         CMode = 0
            #         betaTrav = -5
            #         betaDist = 0
            #         gammaDist = -5e-4 
                    
            #     case "walk":
            #         CMode = 0
            #         betaTrav = -12
            #         betaDist = 0
            #         gammaDist = 0

            #     case "pt":
            #         CMode = 0
            #         betaTrav = -5
            #         betaDist = 0
            #         gammaDist = -0.001
                    
            #     case "bike":
            #         CMode = 0
            #         betaTrav = -12
            #         betaDist = 0
            #         gammaDist = 0
                    
            #     case "bus":
            #         CMode = 0
            #         betaTrav = -5
            #         betaDist = 0
            #         gammaDist = -0.001
                    
            #     case "tram":
            #         CMode = 0
            #         betaTrav = 0
            #         betaDist = 0
            #         gammaDist = -4e-4
                    
            #     case "rail":
            #         CMode = 0
            #         betaTrav = -5
            #         betaDist = 0
            #         gammaDist = -0.001
                    
            #     case "taxi":
            #         CMode = 0
            #         betaTrav = 0
            #         betaDist = 0
            #         gammaDist = -0.002

            #     case "pt":
            #         CMode = 0
            #         betaTrav = -5
            #         betaDist = 0
            #         gammaDist = -0.001
                 
            #     case "ferry":
            #         CMode = 0
            #         betaTrav = -5
            #         betaDist = 0
            #         gammaDist = -0.001

            #     case "access_walk":
            #         CMode = 0
            #         betaTrav = -12
            #         betaDist = 0
            #         gammaDist = 0

            #     case "egress_walk":
            #         CMode = 0
            #         betaTrav = -12
            #         betaDist = 0
            #         gammaDist = 0
                 
            #     case "subway":
            #         CMode = 0
            #         betaTrav = -5
            #         betaDist = 0
            #         gammaDist = -0.001
            #     case _:
            #         print("dodgy travel mode type")
            #         CMode = 0
            #         betaTrav = 0
            #         betaDist = 0
            #         gammaDist = 0
            if trips[i][j] in modes_seen_in_trip:
                CMode = 0  # Mode already used in this trip, set constant to 0
            else:
                modes_seen_in_trip.add(trips[i][j])

            STime = betaTrav*(durations[i][j]/3600)
            # print("STime: "+str(STime))
            # try:
            #     tollcost = -1* assign_tolls(tolls, routes[i][j], trips[i][j])
            # except:
            #     print("tolls failed")
            #     print(id)
            #     tollcost = 0 #REMOVE OR FIX THIS

            try:
                # Get the route for the specific leg                
                leg_toll_val, leg_toll_count = assign_tolls(tolls, routes[i][j], trips[i][j])
                
                total_row_toll_value += leg_toll_val
                total_row_toll_count += leg_toll_count
                
                # Utility uses the negative cost
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
            # print("boardWait: "+str(boardWait[i][j]))
            # print("SWait: "+str(SWait))
            STotal_temp = CMode + STime + SMon + SDist + SWait
            STotal += STotal_temp
        STrans = transferCount * betaTrans #it appears MATSIM does not like to account for transfer penalties!
        # print("Strans: "+str(STrans))
        STotal += STrans
        # print("STotal: "+str(STotal))
        utilities.append(STotal)
    return pd.Series([utilities, total_row_toll_value, total_row_toll_count, totalTransferCount])


def get_activities(activity_modes, activity_indices, stuck_index):
    activities = []
    for i in activity_indices:
        if i<stuck_index:
            activities.append(activity_modes[i])
    return activities

def opening_times_adjust(activities, activity_start_times, activity_end_times):
    new_ast = []
    new_aet = []
    for i in range(len(activities)):
        match activities[i]:
            case "home":
                open = 0
                close = 115200
            case "work":
                open = (7*3600)
                close = (19*3600)+(30*60)
            case "other":
                open = 0
                close = 115200
            case "shop": 
                open = (8*3600)+(30*60)
                close = (19*3600)+(30*60)
            case "education":
                open = (8*3600)+(30*60)
                close = (17*3600)
            case "visit":
                open = 0
                close = 115200
            case "medical":
                open = (9*3600)
                close = (18*3600)
            case "business":
                open = (7*3600)+(30*60)
                close = (20*3600)
            case "escort_home":
                open = 0
                close = 115200
            case "escort_work":
                open = (7*3600)
                close = (19*3600)+(30*60)
            case "escort_business":
                open = (7*3600)
                close = (19*3600)+(30*60)
            case "escort_education":
                open = (8*3600)+(30*60)
                close = (17*3600)
            case "escort_other":
                open = 0
                close = 115200
            case "escort_shop":
                open = (8*3600)+(30*60)
                close = (17*3600)+(30*60) 
            case _:
                print("dodgy activity type: "+str(activities[i]))
                open = np.nan
                close = np.nan
        # match activities[i]:
        #     case "home":
        #         open = 0
        #         close = 32*3600
        #     case "work":
        #         open = 0
        #         close = 32*3600
        #     case "leisure":
        #         open = 0
        #         close = 32*3600
        #     case "shop": 
        #         open = 0
        #         close = 32*3600
        #     case "education":
        #         open = 0
        #         close = 32*3600
        #     case "visit":
        #         open = 0
        #         close = 32*3600
        #     case "medical":
        #         open = 0
        #         close = 32*3600
        #     case "gym":
        #         open = 0
        #         close = 32*3600
        #     case "park":
        #         open = 0
        #         close = 32*3600
        #     case "pub":
        #         open = 0
        #         close = 32*3600
        #     case "business":
        #         open = 0
        #         close = 32*3600
            # case _:
            #     print("dodgy activity type")
            #     open = np.nan
            #     close = np.nan
        if (activity_end_times[i] - activity_start_times[i] <= 1.0) and (i < len(activities)-1):
            # It's missed. Bypass opening hours so it retains its 1s duration and gets penalized
            new_ast.append(activity_start_times[i])
            new_aet.append(activity_end_times[i])
            continue
        
        if activity_start_times[i]<open:
            new_ast.append(open)
        else:
            new_ast.append(activity_start_times[i])

        if activity_end_times[i]>close:
            new_aet.append(close)
        else:
            new_aet.append(activity_end_times[i])
    return(new_ast, new_aet)


def get_activity_timings(activity_indices, all_durations, all_activities_trips):

    activity_start_times = []
    activity_end_times = []
    all_durations = pd.to_timedelta(all_durations, errors="coerce").total_seconds() 
    for i in range(len(activity_indices)):
        # print("new item: "+str(i))
        schedEndTime = all_durations[activity_indices[i]]
        # print(schedEndTime)
        if activity_indices[i]==0:
            startTime = 0
        else:
            prevEndTime = all_durations[activity_indices[i-1]]
            x1 = activity_indices[i-1]+1
            x2 = activity_indices[i]
            startTime = prevEndTime+sum(all_durations[x1:x2]) 

        #COMMENT OUT THE WHOLE OF THE FOLLOWING IF STATEMENT FOR EXPERIENCED PLANS
        if ((startTime >=  86400) and (i != len(activity_indices)-1)) or  ((startTime >= 115200) and (i == len(activity_indices)-1) ):  
        # if (startTime >=  86400) and (startTime < 115200) and (i != len(activity_indices)-1) : 
             stuck_index = activity_indices[i] #stuck index is the index of the activity that does not begin. THIS ONE FOR PLANNED PLANS
            #  stuck_index = activity_indices[-1]+1 #THIS ONE FOR EXPERIENCED PLANS           
             break
        if startTime >= schedEndTime:
            realEndTime = startTime +1
        else:
            realEndTime = schedEndTime
        # stuck_index = activity_indices[-1]+2 #remember that stuck index is related to the total durations index. THIS ONE FOR PLANNED PLANS
        stuck_index = activity_indices[-1]+2 #THIS ONE FOR EXPERIENCED PLANS
        activity_start_times.append(startTime)
        activity_end_times.append(realEndTime)

    #TODO: set end time for stuck agents

    # if (all_activities_trips[0] != all_activities_trips[-1]) & (stuck_index == activity_indices[-1]+2) & (stuck_bool == 0): #so this is for non-wrap, non-stuck agents
    if (all_activities_trips[0] != all_activities_trips[-1]) & (stuck_index == activity_indices[-1]+2): #only set to midnight for non-stuck agents who don't wrap around
        # print("here 1")
        if activity_start_times[-1] >= 24*3600:
            activity_end_times[-1] = activity_start_times[-1]+1
        else:        
            activity_end_times[-1] = 24*3600 #set non-wraparound activities to end at midnight
    # elif (all_activities_trips[0] == all_activities_trips[-1]) & (stuck_index == activity_indices[-1]+2) & (stuck_bool == 0): #for wraparound, non-stuck agents
    elif (all_activities_trips[0] == all_activities_trips[-1]) & (stuck_index == activity_indices[-1]+2): #for wraparound, non-stuck agents
        activity_end_times[-1] = 24*3600 #set to midnight 

    activities = get_activities(all_activities_trips, activity_indices, stuck_index)

    new_activity_start_times, new_activity_end_times = opening_times_adjust(activities, activity_start_times, activity_end_times)

    return(new_activity_start_times, new_activity_end_times, stuck_index) 


def get_activity_durations(activity_starts, activity_ends, all_activities_trips, stuck_index):

    activity_durations = list(map(operator.sub, list(activity_ends), list(activity_starts)))
    
    if (all_activities_trips[0] == all_activities_trips[-1]) & (stuck_index > len(all_activities_trips)):
    # if (all_activities_trips[0] == all_activities_trips[-1]) & (stuck_index > len(all_activities_trips)) & (stuck_bool == 0): #only wrap if activity is same and they don't get stuck
        activity_durations[0] = activity_durations[0]+activity_durations[-1] 
        activity_durations.pop() #remove last activity duration as it has been included in the frist activity
    
    # activity_durations = [1 if i== 0 else i for i in activity_durations ] # handles zero durations from missed activities
    # # print(activity_durations)
    # activity_durations = [i if i>0 else 1 for i in activity_durations ] #handles negative durations from missing opening hours. 1 second bc there has to be something each second (cant be 0) seconds 
    activity_durations = [max(i, 1) for i in activity_durations]


    return(activity_durations)
# TODO: negative durations due to wraparound with final ending after first beginning 


def calculate_activity_utility(activity_modes, activity_indices, stuck_index, durations):
    # print(id)
    activities = get_activities(activity_modes, activity_indices, stuck_index)
    # print(activities)
    utilities = []
    # betaEarly = 0
    # betaLate = 0
    betaPerf = 10 #6 for londinium and 10 for TE
    # betaWait = 0
    # betaShort = 0
    prio = 1
    durations = [a/3600 for a in durations]  #put it back into hours

    if (activities[-1] == activities[0]) & (stuck_index > len(activity_modes)): 
    # if (activities[-1] == activities[0]) & (stuck_index > len(activity_modes)) & (stuck_bool == 0): #remove final activity for wraparound non-stuck agents
        activities.pop() #TODO: ignore this for stuck agents
        # print("here")
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
        # match activities[i]:
        #     case "home":
        #         tMin = 8
        #         tTyp = 12
        #     case "work":
        #         tMin = 8
        #         tTyp = 8.5
        #     case "leisure":
        #         tMin = 0.5
        #         tTyp = 1
        #     case "shop": 
        #         tMin = 0.25
        #         tTyp = 1
        #     case "education":
        #         tMin = 2
        #         tTyp = 6
        #     case "visit":
        #         tMin = 0.5
        #         tTyp = 2
        #     case "medical":
        #         tMin = 5/60
        #         tTyp = 1
        #     case "business":
        #         tMin = 0.5
        #         tTyp = 1
        #     case "park":
        #         tMin = 0.5
        #         tTyp = 1
        #     case "gym":
        #         tMin = 0.5
        #         tTyp = 1.5
        #     case "pub":
        #         tMin = 0.5
        #         tTyp = 1
    
            case _:
                print("dodgy activity type: "+str(activities[i]))
                tMin = np.nan
                tTyp = np.nan
        # print("tTyp: "+str(tTyp))
        t0 = tTyp*np.exp(-1/prio)
        if durations[i]> t0:
            # print("t0: "+str(t0))
            SDur = betaPerf*tTyp*np.log(durations[i]/t0)
        elif durations[i]>0: 
            SDur = -1* betaPerf*tTyp/t0*(t0-durations[i])
        else:
            SDur = 0
        # print(SDur)
        SWait = 0 #since betaWait is zero. Otherwise, will need to encode open/close times for activities to find out how long waiting       
        SLate = 0 #since betaLate is zero. Otherwise, will need to encode latest start times for activities to find out how late   
        SEarly = 0 #since betaEarly is zero. Otherwise, will need to encode earliest end times for activities to find out how early   
        SShort = 0 #since betaEarly is zero/undefined. Otherwise, will need to use shortesr durations for activities to find out if too short   
        STotal_temp = SDur + SWait + SLate + SEarly + SShort
        STotal += STotal_temp
        # print("STotal: "+str(STotal))
        utilities.append(STotal)
    return utilities


def assign_tolls(tolls, route, mode):
    toll_sum_temp = 0.0
    toll_count = 0
    route_list = route.split(' ')
    if mode in ["car", "taxi"] and isinstance(route, str): # Safety check for route strings
        for link_id in route_list[:-1]: #TODO: BUT THIS MAY MISS A TOLL THAT COULD BE ON THE LAST LINK OF THE LAST LEG IF FIRST AND LAST LOC ARE NOT IN THE SAME PLACE.
            if link_id and link_id != "N/A":
                try:
                    val = float(tolls[link_id])
                    if val != 0:
                        toll_sum_temp += val
                        toll_count += 1
                except (KeyError, ValueError):
                    pass 
    return toll_sum_temp, toll_count

def calculate_stuck_penalty(total_activities_modes, stuck_id):
    if stuck_id < len(total_activities_modes):
        penalty = -24*10.5 # hard coded from the data for ease atm
    else:
        penalty = 0
    return penalty
