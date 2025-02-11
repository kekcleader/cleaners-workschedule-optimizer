import optapy
import optapy.types
import optapy.score
import datetime
import enum


@optapy.problem_fact
class Cleaner:
    name: str
    skill_set: list[str]

    def __init__(self, name: str = None, skill_set: list[str] = None):
        self.name = name
        self.skill_set = skill_set

    def __str__(self):
        return f'Cleaner(name={self.name})'

    def to_dict(self):
        return {
            'name': self.name,
            'skill_set': self.skill_set
        }


class AvailabilityType(enum.Enum):
    DESIRED = 'DESIRED'
    UNDESIRED = 'UNDESIRED'
    UNAVAILABLE = 'UNAVAILABLE'

    @staticmethod
    def list():
        return list(map(lambda at: at, AvailabilityType))


@optapy.problem_fact
class Availability:
    cleaner: Cleaner
    date: datetime.date
    availability_type: AvailabilityType

    def __init__(self, cleaner: Cleaner = None, date: datetime.date = None,
                 availability_type: AvailabilityType = None):
        self.cleaner = cleaner
        self.date = date
        self.availability_type = availability_type

    def __str__(self):
        return f'Availability(cleaner={self.cleaner}, date={self.date}, availability_type={self.availability_type})'

    def to_dict(self):
        return {
            'cleaner': self.cleaner.to_dict(),
            'date': self.date.isoformat(),
            'availability_type': self.availability_type.value
        }


class ScheduleState:
    publish_length: int
    draft_length: int
    first_draft_date: datetime.date
    last_historic_date: datetime.date

    def __init__(self, publish_length: int = None, draft_length: int = None, first_draft_date: datetime.date = None,
                 last_historic_date: datetime.date = None):
        self.publish_length = publish_length
        self.draft_length = draft_length
        self.first_draft_date = first_draft_date
        self.last_historic_date = last_historic_date

    def is_draft(self, shift):
        return shift.start >= datetime.datetime.combine(self.first_draft_date, datetime.time.min)

    def to_dict(self):
        return {
            'publish_length': self.publish_length,
            'draft_length': self.draft_length,
            'first_draft_date': self.first_draft_date.isoformat(),
            'last_historic_date': self.last_historic_date.isoformat()
        }


def shift_pinning_filter(solution, shift):
    return not solution.schedule_state.is_draft(shift)


@optapy.planning_entity(pinning_filter=shift_pinning_filter)
class Shift:
    id: int
    start: datetime.datetime
    end: datetime.datetime
    location: str
    required_skill: str
    cleaner: Cleaner

    def __init__(self, id: int = None, start: datetime.datetime = None, end: datetime.datetime = None,
                 location: str = None, required_skill: str = None, cleaner: Cleaner = None):
        self.id = id
        self.start = start
        self.end = end
        self.location = location
        self.required_skill = required_skill
        self.cleaner = cleaner

    @optapy.planning_id
    def get_id(self):
        return self.id

    @optapy.planning_variable(Cleaner, value_range_provider_refs=['cleaner_range'])
    def get_cleaner(self):
        return self.cleaner

    def set_cleaner(self, cleaner):
        self.cleaner = cleaner

    def __str__(self):
        return f'Shift(id={self.id}, start={self.start}, end={self.end}, location={self.location}, ' \
               f'required_skill={self.required_skill}, cleaner={self.cleaner})'

    def to_dict(self):
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'location': self.location,
            'required_skill': self.required_skill,
            'cleaner': self.cleaner.to_dict() if self.cleaner is not None else None
        }


@optapy.planning_solution
class Schedule:
    schedule_state: ScheduleState
    availability_list: list[Availability]
    cleaner_list: list[Cleaner]
    shift_list: list[Shift]
    solver_status: optapy.types.SolverStatus
    score: optapy.score.SimpleScore

    def __init__(self, schedule_state, availability_list, cleaner_list, shift_list, solver_status, score=None):
        self.cleaner_list = cleaner_list
        self.availability_list = availability_list
        self.schedule_state = schedule_state
        self.shift_list = shift_list
        self.solver_status = solver_status
        self.score = score

    @optapy.problem_fact_collection_property(Cleaner)
    @optapy.value_range_provider('cleaner_range')
    def get_cleaner_list(self):
        return self.cleaner_list

    @optapy.problem_fact_collection_property(Availability)
    def get_availability_list(self):
        return self.availability_list

    @optapy.planning_entity_collection_property(Shift)
    def get_shift_list(self):
        return self.shift_list

    @optapy.planning_score(optapy.score.HardSoftScore)
    def get_score(self):
        return self.score

    def set_score(self, score):
        self.score = score

    def to_dict(self):
        return {
            'cleaner_list': list(map(lambda cleaner: cleaner.to_dict(), self.cleaner_list)),
            'availability_list': list(map(lambda availability: availability.to_dict(), self.availability_list)),
            'schedule_state': self.schedule_state.to_dict(),
            'shift_list': list(map(lambda shift: shift.to_dict(), self.shift_list)),
            'solver_status': self.solver_status.toString(),
            'score': self.score.toString(),
        }