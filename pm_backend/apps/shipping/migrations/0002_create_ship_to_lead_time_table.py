from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0001_ship_to_lead_time'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS `m_ship_to_lead_time` (
                `id` bigint AUTO_INCREMENT PRIMARY KEY,
                `ship_to_code` varchar(40) NOT NULL,
                `ship_to_name` varchar(100) NOT NULL DEFAULT '',
                `additional_days` int UNSIGNED NOT NULL DEFAULT 0,
                `is_active` tinyint(1) NOT NULL DEFAULT 1,
                `created_at` datetime(6) NOT NULL,
                `updated_at` datetime(6) NOT NULL,
                `customer_id` bigint NOT NULL,
                CONSTRAINT `fk_ship_to_lt_customer`
                    FOREIGN KEY (`customer_id`) REFERENCES `m_customer` (`id`)
                    ON DELETE CASCADE,
                UNIQUE KEY `uq_ship_to_lt_customer_code` (`customer_id`, `ship_to_code`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            reverse_sql="DROP TABLE IF EXISTS `m_ship_to_lead_time`;",
        ),
    ]
