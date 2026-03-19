"""
Django Management Command to mark absent employees automatically.

This command can be scheduled to run at the end of each day (e.g., via cron)
to automatically create "absent" records for employees who didn't clock in,
and "failed_to_clock_out" for employees who didn't clock out after their shift.

Usage:
    python manage.py mark_absent                  # Mark yesterday as absent
    python manage.py mark_absent --date 2026-02-19  # Mark specific date
    python manage.py mark_absent --dry-run         # Show what would be marked without creating
    python manage.py mark_absent --check-failed    # Check and mark failed_to_clock_out only
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from App.users.models import Staff
from App.human_resource.models import Attendance, EmployeeShiftRule
from datetime import date, timedelta, time, datetime


class Command(BaseCommand):
    help = 'Mark absent employees for a specific date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Target date in YYYY-MM-DD format (default: yesterday)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be marked absent without creating records',
        )
        parser.add_argument(
            '--check-failed',
            action='store_true',
            help='Only check and mark failed_to_clock_out (for employees who did not clock out)',
        )

    def handle(self, *args, **options):
        # Determine target date
        if options['date']:
            target_date = date.fromisoformat(options['date'])
        else:
            # Default to yesterday
            target_date = date.today() - timedelta(days=1)

        check_failed_only = options.get('check_failed', False)

        if check_failed_only:
            self.handle_failed_to_clock_out(target_date, options.get('dry_run', False))
        else:
            # Original behavior: mark absent for employees with no attendance
            self.handle_absent(target_date, options.get('dry_run', False))
            # Also check for failed_to_clock_out
            self.handle_failed_to_clock_out(target_date, options.get('dry_run', False))

    def handle_absent(self, target_date, dry_run=False):
        """Mark employees as absent if they have no attendance record for the date."""
        self.stdout.write(self.style.WARNING(f'\n=== Processing ABSENT for {target_date} ===\n'))

        # Get all active employees (status = 'active')
        active_employees = Staff.objects.filter(status='active')
        
        # Get existing attendance records for the target date
        existing_attendance = Attendance.objects.filter(date=target_date)
        existing_employee_ids = set(existing_attendance.values_list('employee_id', flat=True))

        # Find employees without attendance
        absent_employees = []
        for employee in active_employees:
            if employee.id not in existing_employee_ids:
                absent_employees.append(employee)

        # Show what would happen
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n=== DRY RUN - No records will be created ===\n'))
            self.stdout.write(f'Target Date: {target_date}')
            self.stdout.write(f'Total Active Employees: {active_employees.count()}')
            self.stdout.write(f'Existing Attendance Records: {existing_attendance.count()}')
            self.stdout.write(f'Employees to be marked ABSENT: {len(absent_employees)}\n')
            
            if absent_employees:
                self.stdout.write('List of absent employees:')
                for emp in absent_employees:
                    self.stdout.write(f'  - {emp.first_name} {emp.last_name} ({emp.employee_number})')
            else:
                self.stdout.write(self.style.SUCCESS('All employees have attendance records!'))
            return

        # Create absent records
        created_count = 0
        for employee in absent_employees:
            Attendance.objects.create(
                employee=employee,
                date=target_date,
                status='absent'
            )
            created_count += 1
            self.stdout.write(f'Marked ABSENT: {employee.first_name} {employee.last_name} ({employee.employee_number})')

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n=== Absent Summary ==='))
        self.stdout.write(f'Target Date: {target_date}')
        self.stdout.write(f'Total Active Employees: {active_employees.count()}')
        self.stdout.write(f'Existing Attendance: {existing_attendance.count()}')
        self.stdout.write(f'Records Created (Absent): {created_count}')
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully marked {created_count} employees as absent!'))
        else:
            self.stdout.write(self.style.SUCCESS('\nNo absent records needed - all employees have attendance!'))

    def handle_failed_to_clock_out(self, target_date, dry_run=False):
        """
        Mark employees as failed_to_clock_out if:
        - They have clocked in but NOT clocked out
        - The current time is past their shift's clock_out time + grace period
        """
        self.stdout.write(self.style.WARNING(f'\n=== Processing FAILED TO CLOCK OUT for {target_date} ===\n'))

        # Get attendance records that have clock_in but no clock_out
        incomplete_attendance = Attendance.objects.filter(
            date=target_date,
            clock_in__isnull=False,
            clock_out__isnull=True
        )

        # Get current time
        current_time = timezone.localtime().time()
        current_datetime = datetime.now()
        
        failed_to_clock_out_list = []

        for attendance in incomplete_attendance:
            employee = attendance.employee
            
            # Get employee's shift rule
            shift_rule = EmployeeShiftRule.objects.filter(
                shift=employee.shift, 
                rank=employee.rank
            ).first()

            if not shift_rule or not shift_rule.clock_out:
                # Skip if no shift rule or no clock_out time defined
                continue

            # Calculate deadline (clock_out + grace_period)
            clock_out_time = shift_rule.clock_out
            grace_period = getattr(shift_rule, 'clock_out_grace_period', 60)  # Default 60 minutes
            
            # Convert clock_out to datetime to add minutes
            clock_out_dt = datetime.combine(target_date, clock_out_time)
            deadline_dt = clock_out_dt + timedelta(minutes=grace_period)
            deadline_time = deadline_dt.time()

            # Check if current time is past the deadline
            if current_time > deadline_time:
                failed_to_clock_out_list.append({
                    'attendance': attendance,
                    'employee': employee,
                    'shift_rule': shift_rule,
                    'clock_out': clock_out_time,
                    'deadline': deadline_time
                })

        # Show what would happen
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n=== DRY RUN - No records will be created ===\n'))
            self.stdout.write(f'Target Date: {target_date}')
            self.stdout.write(f'Current Time: {current_time}')
            self.stdout.write(f'Employees with incomplete attendance: {incomplete_attendance.count()}')
            self.stdout.write(f'Employees to be marked FAILED TO CLOCK OUT: {len(failed_to_clock_out_list)}\n')
            
            if failed_to_clock_out_list:
                self.stdout.write('List of employees:')
                for item in failed_to_clock_out_list:
                    emp = item['employee']
                    self.stdout.write(f'  - {emp.first_name} {emp.last_name} ({emp.employee_number}) '
                                      f'- Clock Out: {item["clock_out"]}, Deadline: {item["deadline"]}')
            else:
                self.stdout.write(self.style.SUCCESS('No employees failed to clock out!'))
            return

        # Update status to failed_to_clock_out
        created_count = 0
        for item in failed_to_clock_out_list:
            attendance = item['attendance']
            employee = item['employee']
            
            attendance.status = 'failed_to_clock_out'
            attendance.save()
            
            created_count += 1
            self.stdout.write(f'Marked FAILED TO CLOCK OUT: {employee.first_name} {employee.last_name} ({employee.employee_number})')

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n=== Failed to Clock Out Summary ==='))
        self.stdout.write(f'Target Date: {target_date}')
        self.stdout.write(f'Current Time: {current_time}')
        self.stdout.write(f'Incomplete Attendance: {incomplete_attendance.count()}')
        self.stdout.write(f'Records Updated (Failed to Clock Out): {created_count}')
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully marked {created_count} employees as failed to clock out!'))
        else:
            self.stdout.write(self.style.SUCCESS('\nNo employees failed to clock out!'))

