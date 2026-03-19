# HR Attendance Enhancement Plan

## Overview
This plan implements lunch clock in/out functionality with over-lunch deduction tracking and HR validation for the Rockstar Beta attendance system.

## Requirements Summary
1. **Lunch In/Lunch Out**: Add lunch clock fields to attendance
2. **Over-lunch calculation**: Count extra lunch minutes as deduction when exceeding 60 minutes
3. **HR Validation**: HR can mark over-lunch as valid (excluded from deduction) or invalid (included in deduction)
4. **Deduction formula**: `deduction_mins = (overlunch_mins if not validated) + late_mins`
5. **Floating button**: Add to attendance_list.html for pending items
6. **Pending dropdown**: Filter for overlunch counting + failed to clock out
7. **Shift Rules**: Remove "Clock In End", use only "Clock In Start"
8. **Late calculation**: Use only Clock In Start (not Clock In End)

---

## Implementation Details

### 1. Database Model Changes

#### Attendance Model - New Fields
```
- lunch_in: TimeField (null=True, blank=True)
- lunch_out: TimeField (null=True, blank=True)
- overlunch_minutes: PositiveIntegerField (default=0) - calculated extra lunch minutes
- overlunch_validated: BooleanField (default=False) - HR validation status
- deduction_minutes: PositiveIntegerField (default=0) - total deduction (late + overlunch if not validated)
```

#### EmployeeShiftRule Model - New Fields
```
- lunch_start: TimeField (null=True, blank=True) - standard lunch start time
- lunch_end: TimeField (null=True, blank=True) - standard lunch end time (60 min default)
```

---

### 2. Template Updates

#### attendance_clock.html
- Add Lunch In/Lunch Out buttons in the "Currently Working" section
- Display lunch times in the Today's Summary
- Show overlunch deduction info if applicable
- Update shift schedule display to show lunch times

#### attendance_list.html
- Add floating notification button (bottom-right) for pending items
- Pending = records with overlunch_not_validated OR failed_to_clock_out
- Add dropdown filter option: "Pending" (overlunch counting + failed to clock out)
- Add columns: Lunch In, Lunch Out, Overlunch, Deduction Mins

#### attendance_form.html
- Add Lunch In and Lunch Out time inputs
- Add Overlunch Validated checkbox (for HR use)
- Display calculated deduction minutes
- Show shift schedule with lunch times

#### shift_rules_list.html
- Remove "Clock In End" column
- Keep "Clock In Start" only
- Add Lunch Start and Lunch End columns
- Update instructions text

#### shift_rule_form.html
- Remove Clock In End field
- Add Lunch Start and Lunch End fields

---

### 3. View Updates

#### Late Calculation (attendance_clock.html logic)
```python
# Current: uses clock_in_start and clock_in_end
# New: use ONLY clock_in_start for late calculation
if attendance.clock_in > shift_rule.clock_in_start:
    late_minutes = (clock_in_time - clock_in_start).total_seconds() / 60
```

#### Overlunch Calculation
```python
# Calculate overlunch if both lunch times exist
if attendance.lunch_in and attendance.lunch_out:
    lunch_duration = (lunch_out - lunch_in).total_seconds() / 60
    standard_lunch = 60  # minutes
    overlunch = max(0, lunch_duration - standard_lunch)
    
# Deduction calculation
if not attendance.overlunch_validated:
    deduction = overlunch + late_minutes
else:
    deduction = late_minutes
```

---

### 4. HR Validation Workflow

1. Employee clocks in → works → clocks out for lunch → clocks in from lunch → clocks out
2. System calculates overlunch minutes
3. If overlunch > 0, record appears in HR pending list
4. HR reviews with supervisor, marks as validated or not
5. If validated: no deduction for overlunch
6. If not validated: overlunch added to deduction minutes

---

### 5. Floating Button - Pending Items

```
Location: Bottom-right of attendance_list.html
Trigger: When pending_count > 0
Pending Items:
  - Records with overlunch_not_validated
  - Records with failed_to_clock_out status

Dropdown shows:
  - Employee name
  - Date
  - Issue type (Overlunch / Failed Clock Out)
  - Action button to validate or acknowledge
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `models.py` | Add lunch/overlunch/deduction fields to Attendance; add lunch fields to EmployeeShiftRule |
| `forms.py` | Update forms with new fields |
| `views.py` | Update late calculation, add overlunch calculation, add HR validation view |
| `urls.py` | Add routes for lunch clock, HR validation |
| `attendance_clock.html` | Add lunch in/out buttons and display |
| `attendance_list.html` | Add floating button, pending filter, new columns |
| `attendance_form.html` | Add lunch fields, overlunch validation |
| `shift_rules_list.html` | Remove Clock In End, add Lunch columns |
| `shift_rule_form.html` | Remove Clock In End, add Lunch fields |

---

## Migration Required

```bash
python manage.py makemigrations human_resource
python manage.py migrate
```

---

## Status Tracking

- Pending status option in filter: `overlunch_pending`, `failed_to_clock_out`
- New deduction_minutes field stored in Attendance for payroll calculation
