# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-03-20 18:38
from __future__ import unicode_literals

import django.db.models.deletion
import django_countries.fields
import easy_thumbnails.fields
import userena.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mugshot', easy_thumbnails.fields.ThumbnailerImageField(blank=True, help_text='A personal image displayed in your profile.', upload_to=userena.models.upload_to_mugshot, verbose_name='mugshot')),
                ('privacy', models.CharField(choices=[('open', 'Open'), ('registered', 'Registered'), ('closed', 'Closed')], default='open', help_text='Designates who can view your profile.', max_length=15, verbose_name='privacy')),
                ('institution', models.CharField(max_length=100)),
                ('department', models.CharField(max_length=100)),
                ('country', django_countries.fields.CountryField(max_length=2)),
                ('website', models.CharField(blank=True, max_length=150)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user_profile', to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'permissions': (('view_profile', 'Can view profile'),),
                'abstract': False,
            },
        ),
    ]
