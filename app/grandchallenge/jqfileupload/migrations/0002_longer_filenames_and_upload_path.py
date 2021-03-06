# Generated by Django 2.0.6 on 2018-06-28 12:13

from django.db import migrations, models
import grandchallenge.jqfileupload.models


class Migration(migrations.Migration):

    dependencies = [
        ('jqfileupload', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='stagedfile',
            name='upload_path_sha256',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='stagedfile',
            name='file',
            field=models.FileField(max_length=256, upload_to=grandchallenge.jqfileupload.models.generate_upload_filename),
        ),
    ]
