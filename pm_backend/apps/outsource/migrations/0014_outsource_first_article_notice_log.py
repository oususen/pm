from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outsource', '0013_materialrequirement_issued_by_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutsourceFirstArticleNoticeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_code', models.CharField(max_length=50, verbose_name='品目コード')),
                ('product_number', models.CharField(blank=True, default='', max_length=20, verbose_name='品番')),
                ('item_name', models.CharField(blank=True, default='', max_length=200, verbose_name='品目名称')),
                ('painting_date', models.DateField(verbose_name='塗装日')),
                ('order_qty', models.IntegerField(default=0, verbose_name='数量')),
                ('case_no', models.CharField(blank=True, default='', max_length=100, verbose_name='案件番号')),
                ('notified_at', models.DateTimeField(auto_now_add=True, verbose_name='通知日時')),
            ],
            options={
                'verbose_name': 'FB外作お久しぶり通知ログ',
                'db_table': 'outsource_first_article_notice_log',
                'ordering': ['-notified_at', '-id'],
                'unique_together': {('item_code', 'painting_date', 'case_no')},
            },
        ),
    ]
