from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0053_seed_manual_documents'),
        ('shipping', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS `m_ship_to_lead_time` (
                    `id` bigint NOT NULL AUTO_INCREMENT,
                    `ship_to_code` varchar(40) NOT NULL,
                    `ship_to_name` varchar(100) NOT NULL DEFAULT '',
                    `additional_days` int unsigned NOT NULL DEFAULT 0,
                    `is_active` tinyint(1) NOT NULL DEFAULT 1,
                    `created_at` datetime(6) NOT NULL,
                    `updated_at` datetime(6) NOT NULL,
                    `customer_id` bigint NOT NULL,
                    PRIMARY KEY (`id`),
                    UNIQUE KEY `m_ship_to_lead_time_customer_ship_to_uniq` (`customer_id`, `ship_to_code`),
                    CONSTRAINT `m_ship_to_lead_time_customer_fk`
                        FOREIGN KEY (`customer_id`) REFERENCES `m_customer` (`id`) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            reverse_sql="DROP TABLE IF EXISTS `m_ship_to_lead_time`;",
        ),
    ]
