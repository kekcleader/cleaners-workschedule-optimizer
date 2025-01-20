from domain import Cleaner, Shift, Availability, AvailabilityType, ScheduleState, Schedule
import datetime
from random import Random
from optapy import solver_manager_create, score_manager_create
import optapy.config
from optapy.types import Duration, SolverStatus
from optapy.score import HardSoftScore
from constraints import scheduling_constraints
from typing import Optional
from flask import Flask, jsonify, render_template

app = Flask(__name__)

def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)

FIRST_NAMES = [
    "Artūrs", "Zane", "Mārtiņš", "Elīna", "Jānis", "Laura", "Andris", "Ilze", 
    "Rūta", "Kristaps", "Agnese", "Edgars", "Līga", "Valters", "Dana", "Māris", 
    "Inese", "Anita", "Rolands", "Gundega", "Kaspars", "Linda", "Dainis", "Sanita",
]
LAST_NAMES = [
    "Bērziņš", "Kalniņš", "Ozoliņš", "Liepa", "Kļaviņš", "Grīnbergs", "Ziediņš", 
    "Vītoliņš", "Upenieks", "Siliņš", "Lācis", "Priednieks", "Eglītis", "Zariņš", 
    "Vilks", "Dzenis", "Jansons", "Lejiņš", "Ābele", "Lūsis", "Dārznieks", "Balodis", 
    "Lapsa", "Straume", "Zvejnieks", "Rozītis", "Zemītis", "Gailis", "Vanags", "Eglīte",
    "Dūmiņš", "Baldonis", "Kaļķis", "Bramanis", "Priekulis", "Kalējs", "Silavs", 
]
REQUIRED_SKILLS = ["telpu uzkopšana", "mazgāšana"]
OPTIONAL_SKILLS = ["logu tīrīšana", "servēšana", "dezinfekcija"]
LOCATIONS = ["Sedas iela 17", "Sedas iela 19", "Irbenes iela 24a", "Irbenes iela 24b", "Irbenes iela 25 k-1", "Irbenes iela 25 k-2"]
SHIFT_LENGTH = datetime.timedelta(hours=8)
MORNING_SHIFT_START_TIME = datetime.time(hour=6)
DAY_SHIFT_START_TIME = datetime.time(hour=9)
AFTERNOON_SHIFT_START_TIME = datetime.time(hour=14)
NIGHT_SHIFT_START_TIME = datetime.time(hour=22)
INITIAL_ROSTER_LENGTH_IN_DAYS = 40

SHIFT_START_TIME_COMBOS = (
    (MORNING_SHIFT_START_TIME, AFTERNOON_SHIFT_START_TIME),
    (MORNING_SHIFT_START_TIME, AFTERNOON_SHIFT_START_TIME, NIGHT_SHIFT_START_TIME),
    (MORNING_SHIFT_START_TIME, DAY_SHIFT_START_TIME, AFTERNOON_SHIFT_START_TIME, NIGHT_SHIFT_START_TIME)
)

location_to_shift_start_time_list_dict = dict()
id_generator = 0
schedule: Optional[Schedule] = None

def generate_demo_data():
    global schedule
    START_DATE = next_weekday(datetime.date.today(), 0)

    schedule_state = ScheduleState()
    schedule_state.first_draft_date = START_DATE
    schedule_state.draft_length = INITIAL_ROSTER_LENGTH_IN_DAYS
    schedule_state.publish_length = 7
    schedule_state.last_historic_date = START_DATE

    random = Random(0)

    shift_template_index = 0
    for location in LOCATIONS:
        location_to_shift_start_time_list_dict[location] = SHIFT_START_TIME_COMBOS[shift_template_index]
        shift_template_index = (shift_template_index + 1) % len(SHIFT_START_TIME_COMBOS)

    name_permutations = join_all_combinations(FIRST_NAMES, LAST_NAMES)
    random.shuffle(name_permutations)

    nofcleaners = INITIAL_ROSTER_LENGTH_IN_DAYS * 3 + 10
    cleaner_list = []
    for i in range(nofcleaners):
        skills = pick_subset(OPTIONAL_SKILLS, random, 1, 3)
        skills.append(pick_random(REQUIRED_SKILLS, random))
        cleaner = Cleaner()
        cleaner.name = name_permutations[i]
        cleaner.skill_set = skills
        cleaner_list.append(cleaner)

    shift_list = []
    availability_list = []
    for i in range(INITIAL_ROSTER_LENGTH_IN_DAYS):
        cleaners_with_availabilities_on_day = pick_subset(cleaner_list, random, 4, 3, 2, 1)
        date = START_DATE + datetime.timedelta(days=i)
        for cleaner in cleaners_with_availabilities_on_day:
            availability_type = pick_random(AvailabilityType.list(), random)
            availability = Availability()
            availability.date = date
            availability.cleaner = cleaner
            availability.availability_type = availability_type
            availability_list.append(availability)
        shift_list.extend(generate_shifts_for_day(date, random))

    schedule = Schedule(
        schedule_state,
        availability_list,
        cleaner_list,
        shift_list,
        None
    )

def generate_shifts_for_day(date: datetime.date, random: Random):
    out = []
    for location in LOCATIONS:
        shift_start_time_list = location_to_shift_start_time_list_dict[location]
        for shift_start_time in shift_start_time_list:
            shift_start_date_time = datetime.datetime.combine(date, shift_start_time)
            shift_end_date_time = shift_start_date_time + SHIFT_LENGTH
            out.append(generate_shift_for_timeslot(shift_start_date_time, shift_end_date_time, location, random))
    return out

def generate_shift_for_timeslot(timeslot_start: datetime.datetime, timeslot_end: datetime.datetime,
                                location: str, random: Random):
    global id_generator
    shift_count = random.choices([1, 2], [0.8, 0.2])[0]

    for i in range(shift_count):
        required_skill = None

        if random.randint(0, 1) == 1:
            required_skill = pick_random(REQUIRED_SKILLS, random)
        else:
            required_skill = pick_random(OPTIONAL_SKILLS, random)

        shift = Shift()
        shift.id = id_generator
        shift.start = timeslot_start
        shift.end = timeslot_end
        shift.required_skill = required_skill
        shift.location = location
        shift.cleaner = None
        id_generator += 1
        return shift

def generate_draft_shifts():
    global schedule
    random = Random(0)
    for i in range(schedule.schedule_state.publish_length):
        cleaners_with_availabilities_on_day = pick_subset(schedule.cleaner_list, random, 4, 3, 2, 1)
        date = schedule.schedule_state.first_draft_date + datetime.timedelta(days=(schedule.schedule_state.publish_length + i))
        for cleaner in cleaners_with_availabilities_on_day:
            availability_type = pick_random(AvailabilityType.list(), random)
            availability = Availability()
            availability.date = date
            availability.cleaner = cleaner
            availability.availability_type = availability_type
            schedule.availability_list.append(availability)
        schedule.shift_list.extend(generate_shifts_for_day(date, random))

def pick_random(source: list, random: Random):
    return random.choice(source)

def pick_subset(source: list, random: Random, *distribution: int):
    item_count = random.choices(range(len(distribution)), distribution)
    return random.sample(source, item_count[0])

def join_all_combinations(*part_arrays: list[str]):
    if len(part_arrays) == 0:
        return []
    if len(part_arrays) == 1:
        return part_arrays[0]
    combinations = []
    for combination in join_all_combinations(*part_arrays[1:]):
        for item in part_arrays[0]:
            combinations.append(f'{item} {combination}')
    return combinations

SINGLETON_ID = 1
solver_config = optapy.config.solver.SolverConfig()
solver_config\
    .withSolutionClass(Schedule)\
    .withEntityClasses(Shift)\
    .withConstraintProviderClass(scheduling_constraints)\
    .withTerminationSpentLimit(Duration.ofSeconds(60))

solver_manager = solver_manager_create(solver_config)
score_manager = score_manager_create(solver_manager)
last_score = HardSoftScore.ZERO

@app.route('/schedule')
def get_schedule():
    global schedule
    solution = schedule
    solution.score = score_manager.updateScore(solution)
    solution.solver_status = get_solver_status()
    return jsonify(solution.to_dict())

@app.route('/status')
def get_status():
    global schedule
    status = get_solver_status()
    str = 'ready' if status == SolverStatus.NOT_SOLVING else 'pending'
    return {'status': str}

def get_solver_status():
    return solver_manager.getSolverStatus(SINGLETON_ID)

def error_handler(problem_id, exception):
    print(f'an exception occurred solving {problem_id}: {exception.getMessage()}')
    exception.printStackTrace()

@app.route('/solve', methods=['POST'])
def solve():
    solver_manager.solveAndListen(SINGLETON_ID, find_by_id, save, error_handler)
    return dict()

@app.route('/')
def home():
    return render_template('index.html')

def find_by_id(schedule_id):
    global schedule
    if schedule_id != SINGLETON_ID:
        raise ValueError(f'There is no schedule with id ({schedule_id})')
    return schedule

def save(solution):
    global schedule
    schedule = solution