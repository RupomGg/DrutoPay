from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_remove_user_phone_number'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerIdAllocation',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'customer id allocation',
                'db_table': 'accounts_customer_id_allocation',
            },
        ),
    ]
