from django.db import models

from masters.models import Equipment
from .models_process_work_session import ProcessWorkSession


class ProcessWorkSessionEquipment(models.Model):
    """工程作業セッションに紐づく設備（複数対応）。"""

    ROLE_PRIMARY = 'PRIMARY'
    ROLE_SUB = 'SUB'
    ROLE_CHOICES = [
        (ROLE_PRIMARY, '主設備'),
        (ROLE_SUB, '副設備'),
    ]

    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        ProcessWorkSession,
        on_delete=models.CASCADE,
        related_name='session_equipments',
        verbose_name='作業セッション',
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='設備',
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_SUB,
        verbose_name='設備区分',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 't_process_work_session_equipment'
        verbose_name = '工程作業セッション設備'
        verbose_name_plural = '工程作業セッション設備'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'equipment'],
                name='uniq_pws_equipment',
            ),
        ]
        indexes = [
            models.Index(fields=['session'], name='pws_eq_session_idx'),
            models.Index(fields=['equipment'], name='pws_eq_equipment_idx'),
        ]

    def __str__(self):
        eq = self.equipment.equipment_code if self.equipment_id and self.equipment else 'NONE'
        return f"session:{self.session_id} equipment:{eq}"
