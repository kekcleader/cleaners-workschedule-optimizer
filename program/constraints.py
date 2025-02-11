from optapy import constraint_provider
from optapy.score import HardSoftScore
from optapy.constraint import ConstraintFactory, Joiners
from domain import Shift, Availability, AvailabilityType
from datetime import timedelta, datetime

def get_start_of_availability(availability: Availability):
    return datetime.combine(availability.date, datetime.min.time())


def get_end_of_availability(availability: Availability):
    return datetime.combine(availability.date, datetime.max.time())


def get_minute_overlap(shift1: Shift, shift2: Shift) -> int:
    duration_of_overlap: timedelta = min(shift1.end, shift2.end) - max(shift1.start, shift2.start)
    return int(duration_of_overlap.total_seconds() // 60)


def get_shift_duration_in_minutes(shift: Shift) -> int:
    return int((shift.end - shift.start).total_seconds() // 60)


@constraint_provider
def scheduling_constraints(constraint_factory: ConstraintFactory):
    return [
        required_skill(constraint_factory),
        no_overlapping_shifts(constraint_factory),
        at_least_10_hours_between_two_shifts(constraint_factory),
        one_shift_per_day(constraint_factory),
        unavailable_cleaner(constraint_factory),
        desired_day_for_cleaner(constraint_factory),
        undesired_day_for_cleaner(constraint_factory),
    ]


def required_skill(constraint_factory: ConstraintFactory):
    return constraint_factory \
        .for_each(Shift) \
        .filter(lambda shift: shift.required_skill not in shift.cleaner.skill_set) \
        .penalize("Missing required skill", HardSoftScore.ONE_HARD)


def no_overlapping_shifts(constraint_factory: ConstraintFactory):
    return constraint_factory \
        .for_each_unique_pair(Shift,
                              Joiners.equal(lambda shift: shift.cleaner),
                              Joiners.overlapping(lambda shift: shift.start,
                                                  lambda shift: shift.end)
                              ) \
        .penalize("Overlapping shift", HardSoftScore.ONE_HARD, get_minute_overlap)


def at_least_10_hours_between_two_shifts(constraint_factory: ConstraintFactory):
    TEN_HOURS_IN_SECONDS = 60 * 60 * 10
    return constraint_factory \
        .for_each_unique_pair(Shift,
                              Joiners.equal(lambda shift: shift.cleaner),
                              Joiners.less_than_or_equal(lambda shift: shift.end,
                                                         lambda shift: shift.start)
                              ) \
        .filter(lambda first_shift, second_shift:
                (second_shift.start - first_shift.end).total_seconds() < TEN_HOURS_IN_SECONDS) \
        .penalize("At least 10 hours between 2 shifts", HardSoftScore.ONE_HARD,
                  lambda first_shift, second_shift:
                  (TEN_HOURS_IN_SECONDS - (second_shift.start - first_shift.end).total_seconds()) // 60)


def one_shift_per_day(constraint_factory: ConstraintFactory):
    return constraint_factory \
        .for_each_unique_pair(Shift,
                              Joiners.equal(lambda shift: shift.cleaner),
                              Joiners.equal(lambda shift: shift.start.date())
                              ) \
        .penalize("Max one shift per day", HardSoftScore.ONE_HARD)


def unavailable_cleaner(constraint_factory: ConstraintFactory):
    return constraint_factory \
        .for_each(Shift) \
        .join(Availability,
              Joiners.equal(lambda shift: shift.cleaner,
                            lambda availability: availability.cleaner),
              Joiners.equal(lambda shift: shift.start.date(),
                            lambda availability: availability.date)
              ) \
        .filter(lambda shift, availability: availability.availability_type == AvailabilityType.UNAVAILABLE) \
        .penalize('Unavailable cleaner', HardSoftScore.ONE_HARD,
                  lambda shift, availability: get_shift_duration_in_minutes(shift))


def desired_day_for_cleaner(constraint_factory: ConstraintFactory):
    return constraint_factory \
        .for_each(Shift) \
        .join(Availability,
              Joiners.equal(lambda shift: shift.cleaner,
                            lambda availability: availability.cleaner),
              Joiners.equal(lambda shift: shift.start.date(),
                            lambda availability: availability.date)
              ) \
        .filter(lambda shift, availability: availability.availability_type == AvailabilityType.DESIRED) \
        .reward('Desired day for cleaner', HardSoftScore.ONE_SOFT,
                lambda shift, availability: get_shift_duration_in_minutes(shift))


def undesired_day_for_cleaner(constraint_factory: ConstraintFactory):
    return constraint_factory \
        .for_each(Shift) \
        .join(Availability,
              Joiners.equal(lambda shift: shift.cleaner,
                            lambda availability: availability.cleaner),
              Joiners.equal(lambda shift: shift.start.date(),
                            lambda availability: availability.date)
              ) \
        .filter(lambda shift, availability: availability.availability_type == AvailabilityType.UNDESIRED) \
        .penalize('Undesired day for cleaner', HardSoftScore.ONE_SOFT,
                  lambda shift, availability: get_shift_duration_in_minutes(shift))