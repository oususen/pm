from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='parent_id',
        related_name='children',
    )
    display_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'proposals_department'


class Employee(models.Model):
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=254)
    position = models.CharField(max_length=100)
    role = models.CharField(max_length=20)
    is_active = models.BooleanField()
    joined_on = models.DateField(null=True, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        db_column='department_id',
        related_name='employees',
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_column='user_id',
        related_name='employee_profile',
    )
    division = models.CharField(max_length=100)
    group_name = models.CharField(max_length=100, db_column='group')
    team_name = models.CharField(max_length=100, db_column='team')
    employment_type = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'proposals_employee'


class EmployeePermission(models.Model):
    resource = models.CharField(max_length=50)
    can_view = models.BooleanField()
    can_edit = models.BooleanField()
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        db_column='employee_id',
        related_name='permissions',
    )

    class Meta:
        managed = False
        db_table = 'proposals_employeepermission'
